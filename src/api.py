from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
import docker
import json
from jsonschema import validate
from jsonschema.exceptions import ValidationError
from functools import wraps
from flask import Blueprint, make_response, request
from sqlalchemy import update, insert

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
    if user is None:
      return json_fail("Unauthorized", 401)
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
  
  conn = engine.connect()
  instance = conn.execute(
    History.select().where(
      AvailableInstances.c.key == data["name"],
      History.c.player == data["player"],
      History.c.expiry_time > datetime.now(),
    )
  ).fetchone()
  if instance is None:
    return json_success({"active": False})
  
  detail = conn.execute(
    AvailableInstances.select().where(
      AvailableInstances.c.id == instance.instance
    )
  ).fetchone()
  
  host = instance.host
  port = instance.port
  
  connstr = detail.connstr.replace("HOST", host).replace("PORT", str(port))
  expiry = round(datetime.timestamp(instance.expiry_time))
  
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
      "duration": {"type": "integer"},
      "flag": {"type": "string"},
    },
    "required": ["name", "player", "duration", "flag"],
  }
  
  try:
    validate(instance=data, schema=schema)
  except ValidationError:
    return json_fail("Bad request", 400)
    
  conn = engine.connect()
  instance = conn.execute(
    History.select().where(
      AvailableInstances.c.key == data["name"],
      History.c.player == data["player"],
      History.c.expiry_time > datetime.now(),
    )
  ).fetchone()
  if instance is not None:
    return json_fail("An active instance already exists", 404)
  
  detail = conn.execute(
    AvailableInstances.select().where(
      AvailableInstances.c.key == data["name"]
    )
  ).fetchone()
  if detail is None:
    return json_fail("No container with that key exists", 404)
  
  client = docker.from_env()
  config = json.loads(detail.config)
  config["detach"] = True
  if "environment" not in config:
    config["environment"] = {}
  config["environment"]["FLAG"] = data["flag"]
  config["environment"]["JAIL_ENV_FLAG"] = data["flag"]
  try:
    container = client.containers.run(detail.image_name, **config)
  except docker.errors.ImageNotFound:
    return json_fail("The container ID does not exist. Please contact an admin", 500)
  container.reload()
  #import code
  #code.interact(local=locals())
  try:
    port = int(container.ports[next(iter(container.ports))][0]["HostPort"])
  except StopIteration:
    if container.status == "exited":
      return json_fail("The container failed to start. Please contact an admin", 500)
    else:
      container.stop(timeout=0)
      container.remove()
      return json_fail("The container did not expose a port. Please contact an admin", 500)
  conn.execute(
    insert(History).
    values(instance=detail.id, player=data["player"], token="# TODO",
           request_time=datetime.now(), expiry_time=datetime.now()+timedelta(days=30),
           flag=data["flag"], host=settings["host"], port=port, docker_id=container.id)
  ) # TODO add token field and expiry
  conn.commit()
  
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

  conn = engine.connect()
  instance = conn.execute(
    History.select().where(
      AvailableInstances.c.key == data["name"],
      History.c.player == data["player"],
      History.c.expiry_time > datetime.now(),
    )
  ).fetchone()
  if instance is None:
    return json_fail("This instance is not active", 404)
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
    return json_fail("This instance is not active", 404)
  container.stop(timeout=0)
  container.remove()
  conn.execute(
    update(History).
    where(History.c.id == instance.id).
    values(expiry_time=datetime.now())
  )
  conn.commit()
  
  return json_success(True)
