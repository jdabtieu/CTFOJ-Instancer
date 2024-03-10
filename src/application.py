from datetime import datetime
from flask import Flask, render_template, redirect, flash, send_from_directory
from flask_session import Session
from flask_wtf.csrf import CSRFProtect
import json
from secrets import token_hex
from sqlalchemy import insert, update, delete
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import *
from db import engine, History, Images, Users, Tokens
from api import api

# Flask
app = Flask(__name__)
app.config.from_object("settings")
Session(app)
csrf = CSRFProtect(app)
csrf.init_app(app)
app.register_blueprint(api, url_prefix="/api/v1")
csrf.exempt(api)

@app.route("/login", methods=["GET", "POST"])
def login():
  session.clear()
  session.permanent = True
  
  if request.method == "GET":
    return render_template("auth/login.html")
  
  conn = engine.connect()
  user = conn.execute(
    Users.select().where(Users.c.username==request.form.get("username"))
  ).fetchone()
  conn.close()
  if user is None or not check_password_hash(user.password, request.form.get("password")):
    flash("Incorrect credentials", "danger")
    return render_template("auth/login.html")
  
  session["uid"] = user.id
  session["username"] = user.username
  
  next_url = request.args.get("next")
  if next_url and "//" not in next_url and ":" not in next_url:
    return redirect(next_url)
  return redirect("/")

@app.route("/logout")
def logout():
  session.clear()
  return redirect("/login")

@app.route("/")
@login_required
def dashboard():
  return render_template("dashboard.html")

@app.route("/instances")
@login_required
def active_instances():
  conn = engine.connect()
  instances = conn.execute(
    History.select().where(History.c.expiry_time > datetime.now())
  ).fetchall()
  images = conn.execute(
    Images.select()
  ).fetchall()
  conn.close()
  images = {x.id: x for x in images}
  data = [{
    "name": images[x.instance].key,
    "team": x.player,
    "start_time": str(x.request_time),
    "expire_time": str(x.expiry_time),
    "flag": x.flag,
    "connection": images[x.instance].connstr.replace("HOST", x.host).replace("PORT", str(x.port)),
  } for x in instances]
  
  return render_template("active_instances.html", data=data)

@app.route("/history")
@login_required
def history():
  conn = engine.connect()
  instances = conn.execute(
    History.select()
  ).fetchall()
  images = conn.execute(
    Images.select()
  ).fetchall()
  conn.close()
  images = {x.id: x for x in images}
  data = [{
    "name": images[x.instance].key,
    "team": x.player,
    "start_time": str(x.request_time),
    "expire_time": str(x.expiry_time),
    "flag": x.flag,
    "connection": images[x.instance].connstr.replace("HOST", x.host).replace("PORT", str(x.port)),
  } for x in instances]
  
  return render_template("history.html", data=data[::-1])

@app.route("/images")
@login_required
def images():
  conn = engine.connect()
  images = conn.execute(
    Images.select()
  ).fetchall()
  conn.close()
  return render_template("images.html", data=images)
  
@app.route("/image/create", methods=["GET", "POST"])
@login_required
def create_image():
  if request.method == "GET":
    return render_template("create_image.html")

  # Reached via POST
  key = request.form.get("key")
  image_name = request.form.get("image_name")
  config = request.form.get("config")
  is_global = bool(request.form.get("global"))
  connstr = request.form.get("connstr")
  duration = int(request.form.get("duration"))
    
  if not key or not image_name or not config or not connstr or not duration:
    flash('You have not entered all required fields', 'danger')
    return render_template("create_image.html"), 400

  # Check if fields are valid
  if duration < 1:
    flash('Duration must be at least 1 second', 'danger')
    return render_template("create_image.html"), 400
  try:
    json.loads(config)
  except ValueError:
    flash('Invalid config', 'danger')
    return render_template("create_image.html"), 400

  # Ensure problem does not already exist
  conn = engine.connect()
  image = conn.execute(
    Images.select().where(Images.c.key == key)
  ).fetchone()
  if image is not None:
    conn.close()
    flash('This key is already registered', 'danger')
    return render_template("create_image.html"), 409
  
  conn.execute(
    insert(Images).
    values(key=key, image_name=image_name, config=config,
           is_global=is_global, connstr=connstr, duration=duration)
  )
  conn.commit()
  conn.close()
    
  flash('Image successfully created', 'success')
  return redirect("/images")


@app.route("/image/edit/<id>", methods=["GET", "POST"])
@login_required
def edit_image(id):
  # Get image
  conn = engine.connect()
  image = conn.execute(
    Images.select().where(Images.c.id == id)
  ).fetchone()
  if not image:
    conn.close()
    flash('This image does not exist', 'danger')
    return redirect("/images")
  
  if request.method == "GET":
    return render_template("edit_image.html", data=image)

  # Reached via POST
  key = request.form.get("key")
  image_name = request.form.get("image_name")
  config = request.form.get("config")
  is_global = bool(request.form.get("global"))
  connstr = request.form.get("connstr")
  duration = int(request.form.get("duration"))
    
  if not key or not image_name or not config or not connstr or not duration:
    flash('You have not entered all required fields', 'danger')
    return render_template("edit_image.html"), 400

  # Check if fields are valid
  if duration < 1:
    flash('Duration must be at least 1 second', 'danger')
    return render_template("edit_image.html"), 400
  try:
    json.loads(config)
  except ValueError:
    flash('Invalid config', 'danger')
    return render_template("edit_image.html"), 400
  
  conn.execute(
    update(Images).
    where(Images.c.id == id).
    values(key=key, image_name=image_name, config=config,
           is_global=is_global, connstr=connstr, duration=duration)
  )
  conn.commit()
  conn.close()
    
  flash('Image successfully edited', 'success')
  return redirect("/images")



@app.route("/tokens")
@login_required
def tokens():
  conn = engine.connect()
  tokens = conn.execute(
    Tokens.select()
  ).fetchall()
  conn.close()
  return render_template("tokens.html", data=tokens)

@app.route("/tokens/revoke", methods=["POST"])
@login_required
def revoke_token():
  id = request.form.get("id")
  if not id:
    flash("Must provide token ID", "danger")
    return redirect("/tokens")
  conn = engine.connect()
  conn.execute(
    delete(Tokens).
    where(Tokens.c.id == id)
  )
  conn.commit()
  conn.close()
  flash("Successfully deleted", "success")
  return redirect("/tokens")

@app.route("/tokens/add", methods=["POST"])
@login_required
def add_token():
  name = request.form.get("name")
  if not id:
    flash("Must provide token name", "danger")
    return redirect("/tokens")
  key = token_hex(48)
  conn = engine.connect()
  conn.execute(
    insert(Tokens).
    values(name=name, key=key)
  )
  conn.commit()
  conn.close()
  flash("Successfully created new token.", "success")
  flash(f"The token is {key}", "success")
  return redirect("/tokens")

@app.route("/assets/<path:filename>")
def get_asset(filename):
  resp = send_from_directory("assets/", filename)
  resp.headers["Cache-Control"] = "max-age=604800"
  return resp


if __name__ == "__main__":
  app.run(debug=True, port=5000)
