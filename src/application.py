from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
from flask import Flask, render_template, redirect, flash, send_from_directory
from flask_session import Session
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import *
from db import engine, History, AvailableInstances, Users, Tokens
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
  if user is None or not check_password_hash(user[2], request.form.get("password")):
    flash("Incorrect credentials", "danger")
    return render_template("auth/login.html")
  
  session["uid"] = user[0]
  session["username"] = user[1]
  
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
    AvailableInstances.select()
  ).fetchall()
  images = {x[0]: x for x in images}
  data = [{
    "name": images[x[1]][1],
    "team": x[2],
    "start_time": str(x[4]),
    "expire_time": str(x[5]),
    "flag": x[6],
    "connection": images[x[1]][5].replace("HOST", x[7]).replace("PORT", str(x[8])),
  } for x in instances]
  
  return render_template("active_instances.html", data=data)

"""
  'history', meta,
  Column('id', Integer, primary_key=True),
  Column('instance', ForeignKey('available_instances.id'), nullable=False),
  Column('player', Integer, nullable=False),
  Column('token', ForeignKey('tokens.id'), nullable=False),
  Column('request_time', DateTime, nullable=False),
  Column('expiry_time', DateTime, nullable=False),
  Column('flag', String, nullable=False),
  Column('host', String, nullable=False),
  Column('port', Integer, nullable=False),
  
  AvailableInstances = Table(
  'available_instances', meta,
  Column('id', Integer, primary_key=True),
  Column('key', String, unique=True, nullable=False),
  Column('image_name', String, nullable=False),
  Column('config', String, nullable=False),
  Column('global', Boolean, nullable=False),
  Column('connstr', String, nullable=False),
)

  """

@app.route("/history")
@login_required
def history():
  return render_template("history.html")

@app.route("/images")
@login_required
def images():
  return render_template("images.html")

@app.route("/tokens")
@login_required
def tokens():
  return render_template("tokens.html")

@app.route("/assets/<path:filename>")
def get_asset(filename):
  resp = send_from_directory("assets/", filename)
  resp.headers["Cache-Control"] = "max-age=604800"
  return resp


if __name__ == "__main__":
  app.run(debug=True, port=5000)
