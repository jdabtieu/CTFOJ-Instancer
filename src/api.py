from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import json
from jsonschema import validate
from jsonschema.exceptions import ValidationError
from functools import wraps
from flask import Blueprint, make_response, request

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
      AvailableInstances.c.id == instance[1]
    )
  ).fetchone()
  
  host = instance[7]
  port = instance[8]
  
  connstr = detail[4].replace("HOST", host).replace("PORT", str(port))
  expiry = round(datetime.timestamp(instance[5]))
  
  return json_success({"active": True, "conn": connstr, "expiry": expiry})

@api.route("/create", methods=["POST"])
def create_instance():
  pass

@api.route("/destroy", methods=["POST"])
def destroy_instance():
  pass
