from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
import docker
import json
from jsonschema import validate
from jsonschema.exceptions import ValidationError
from functools import wraps
from flask import Blueprint, make_response, request
from sqlalchemy import func, update, insert, select

from db import engine, History, AvailableInstances, Tokens

# Task scheduler
# For destroying Docker containers upon expiry
scheduler = BackgroundScheduler({
  'apscheduler.jobstores.default': {
    'type': 'sqlalchemy',
    'url': 'sqlite:///jobs.sqlite'
  },
  'apscheduler.timezone': 'UTC',
})

settings = {}
settings["host"] = "localhost"

# Flask
api = Blueprint("api", __name__)

def json_fail(message, http_code):
  return make_response((json.dumps({"status": "fail", "message": message}), http_code))

def json_success(data):
  return json.dumps({"status": "success", "data": data})

def api_authorized(f):
  @wraps(f)
  def decorated_function(*args, **kwargs):
    header = request.headers.get("Authorization")
    if not header or not header.startswith("Bearer "):
      return json_fail("Unauthorized", 401)
    token = header[len("Bearer "):]
    conn = engine.connect()
    user = conn.execute(
      Tokens.select().where(Tokens.c.key == token)
    ).fetchone()
    conn.close()
    if user is None:
      return json_fail("Unauthorized", 401)
    request.token = token
    return f(*args, **kwargs)
  return decorated_function

@api.route("/query", methods=["POST"])
@api_authorized
def query_instance():
  data = request.json
  schema = {
    "type": "object",
    "properties": {
      "name": {"type": "string"},
      "player": {"type": "integer"},
    },
    "required": ["name", "player"],
  }
  
  try:
    validate(instance=data, schema=schema)
  except ValidationError:
    return json_fail("Bad request", 400)
  
  # Get the image spec
  conn = engine.connect()
  detail = conn.execute(
    AvailableInstances.select().where(
      AvailableInstances.c.key == data["name"]
    )
  ).fetchone()
  if detail is None:
    conn.close()
    return json_fail("No container with that key exists", 404)

  # Query the instance metadata
  instance = conn.execute(
    History.select().where(
      History.c.instance == detail.id,
      History.c.player == data["player"],
      History.c.expiry_time > datetime.now(),
    )
  ).fetchone()
  if instance is None:
    conn.close()
    return json_success({"active": False})
  
  # Construct the connection string
  host = instance.host
  port = instance.port
  connstr = detail.connstr.replace("HOST", host).replace("PORT", str(port))
  expiry = round(datetime.timestamp(instance.expiry_time))
  
  conn.close()
  return json_success({"active": True, "conn": connstr, "expiry": expiry})

@api.route("/create", methods=["POST"])
@api_authorized
def create_instance():
  data = request.json
  schema = {
    "type": "object",
    "properties": {
      "name": {"type": "string"},
      "player": {"type": "integer"},
      "flag": {"type": "string"},
    },
    "required": ["name", "player", "flag"],
  }
  
  try:
    validate(instance=data, schema=schema)
  except ValidationError:
    return json_fail("Bad request", 400)

  # Get the image spec
  conn = engine.connect()
  detail = conn.execute(
    AvailableInstances.select().where(
      AvailableInstances.c.key == data["name"]
    )
  ).fetchone()
  if detail is None:
    conn.close()
    return json_fail("No container with that key exists", 404)

  # Rate limit to 4 simultaneous active instances
  instance_cnt = conn.execute(
    select(func.count(History.c.id)).where(
      History.c.player == data["player"],
      History.c.expiry_time > datetime.now(),
    )
  ).scalar_one()
  if instance_cnt >= 4:
    conn.close()
    return json_fail("Please destroy your other instances before creating more", 429)
  
  # Make sure an instance doesn't already exist
  instance = conn.execute(
    History.select().where(
      History.c.instance == detail.id,
      History.c.player == data["player"],
      History.c.expiry_time > datetime.now(),
    )
  ).fetchone()
  if instance is not None:
    conn.close()
    return json_fail("An active instance already exists", 404)
  
  # Grab the challenge spec and prepare flag
  config = json.loads(detail.config)
  config["detach"] = True
  if "environment" not in config:
    config["environment"] = {}
  config["environment"]["FLAG"] = data["flag"]
  config["environment"]["JAIL_ENV_FLAG"] = data["flag"]
  
  # Start the container
  try:
    client = docker.from_env()
    container = client.containers.run(detail.image_name, **config)
  except docker.errors.ImageNotFound:
    conn.close()
    return json_fail("The container ID does not exist. Please contact an admin", 500)
    
  # Grab the port
  container.reload()
  try:
    port = int(container.ports[next(iter(container.ports))][0]["HostPort"])
  except StopIteration:
    conn.close()
    if container.status == "exited":
      return json_fail("The container failed to start. Please contact an admin", 500)
    else:
      container.stop(timeout=0)
      container.remove()
      return json_fail("The container did not expose a port. Please contact an admin", 500)
  
  # Create a db entry
  expiry = datetime.now() + timedelta(seconds=detail.duration)
  conn.execute(
    insert(History).
    values(instance=detail.id, player=data["player"], token=request.token,
           request_time=datetime.now(), expiry_time=expiry, flag=data["flag"],
           host=settings["host"], port=port, docker_id=container.id)
  )
  conn.commit()
  scheduler.add_job(_destroy_instance, 'date', run_date=expiry, args=[data])
  conn.close()
  return query_instance()

@api.route("/destroy", methods=["POST"])
@api_authorized
def destroy_instance():
  data = request.json
  schema = {
    "type": "object",
    "properties": {
      "name": {"type": "string"},
      "player": {"type": "integer"},
    },
    "required": ["name", "player"],
  }
  
  try:
    validate(instance=data, schema=schema)
  except ValidationError:
    return json_fail("Bad request", 400)
  return _destroy_instance(data)

def _destroy_instance(data):
  # Get the image spec
  conn = engine.connect()
  detail = conn.execute(
    AvailableInstances.select().where(
      AvailableInstances.c.key == data["name"]
    )
  ).fetchone()
  if detail is None:
    conn.close()
    return json_fail("No container with that key exists", 404)

  # Get the running instance's metadata
  instance = conn.execute(
    History.select().where(
      History.c.instance == detail.id,
      History.c.player == data["player"],
      History.c.expiry_time > datetime.now(),
    )
  ).fetchone()
  if instance is None:
    conn.close()
    return json_fail("This instance is not active", 404)
  
  # Get the running instance's Docker data
  client = docker.from_env()
  try:
    container = client.containers.get(instance.docker_id)
  except docker.errors.NotFound:
    # Something bad must have happened, might as well clear it
    conn.execute(
      update(History).
      where(History.c.id == instance.id).
      values(expiry_time=datetime.now())
    )
    conn.commit()
    conn.close()
    return json_fail("This instance is not active", 404)
  
  # Kill the container and update the stop time
  container.stop(timeout=0)
  container.remove()
  conn.execute(
    update(History).
    where(History.c.id == instance.id).
    values(expiry_time=datetime.now())
  )
  conn.commit()
  conn.close()
  return json_success(True)
