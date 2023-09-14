from getpass import getpass
from secrets import token_hex
from sqlalchemy import insert
from werkzeug.security import generate_password_hash

from db import *

meta.create_all(engine)
conn = engine.connect()

# Create admin user
password = generate_password_hash(getpass("Admin Password: "))
conn.execute(
    insert(Users).
    values(username="admin", password=password)
)

# Create access token
token = token_hex(48)  # 384 bits
conn.execute(
    insert(Tokens).
    values(name="Default", key=token)
)

conn.commit()

print("Now, go edit CTFOJ's settings.py.")
print("For INSTANCER_TOKEN, enter the following:")
print(f"  {token}\n")
print("For INSTANCER_HOST, enter the hostname of this server")
print("with the http(s)://. For example, http://instancer.my.ctf.")
print("Then, edit CTFOJ-Instancer's settings.py and fill in the")
print("same instancer host and a secure random secret key.")
