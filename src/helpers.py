from flask import session, redirect, request
from functools import wraps
import re

def login_required(f):
  @wraps(f)
  def decorated_function(*args, **kwargs):
    if session.get("uid") is None:
      return redirect("/login?next=" + request.path)
    return f(*args, **kwargs)
  return decorated_function

def verify_id(text):
  """
  Check if text only contains A-Z, a-z, 0-9, underscores, and dashes
  """
  return bool(re.match(r'^[\w\-]+$', text))
