# CTFOJ-Instancer
Instancer for secure CTF challenges hosted with CTFOJ

## Installation
CTFOJ-Instancer is a web app, and to start using it:
- Run it under Ubuntu or Debian (untested for other Unix distros, probably won't work under Windows)
- Run it as a web server (ideally, port 443) and make it available at some public IP/domain
  - Install the dependencies in requirements.txt as well as Docker Engine
  - Use a WSGI server to point to application.py
  - Ideally proxy that through nginx
- Create an API token
- Add the instancer's IP/domain name and token to CTFOJ's settings.py
- Ensure ports 443 and 32768+ are not blocked by a firewall

## Setting up instances
- Build and tag a Docker image corresponding to your challenge on the CTFOJ-Instancer server
- In CTFOJ, check the box for instancing when creating/editing a problem
- Copy the instancer key and in CTFOJ-Instancer, use it to create an instance along with the Docker image tag
- If done correctly, on CTFOJ, the problem will display a box to deploy and instance, and when you click create instance, an instance is created

## Sample API Usage
While instances will be managed by CTFOJ, you can do manual testing on the instancer API.

### To create an instance:
```
curl -H "Authorization: Bearer API_TOKEN" -H "Content-Type: application/json" -X POST --data '{"name": "typop", "player": 1, "duration": 600, "flag": "ctf{flag}"}' http://localhost:5000/api/v1/create
```
The `name` is the challenge key, `player` is the CTFOJ user ID of the player, `duration` is current unused(?), `flag` is the challenge flag, which will be loaded to the environment variables `FLAG` and `JAIL_ENV_FLAG`.

### To query an instance:
```
curl -H "Authorization: Bearer API_TOKEN" -H "Content-Type: application/json" -X POST --data '{"name": "typop", "player": 1}' http://localhost:5000/api/v1/query
```
The `name` is the challenge key, `player` is the CTFOJ user ID of the player.

### To destroy an instance:
```
curl -H "Authorization: Bearer API_TOKEN" -H "Content-Type: application/json" -X POST --data '{"name": "typop", "player": 1}' http://localhost:5000/api/v1/destroy
```
The `name` is the challenge key, `player` is the CTFOJ user ID of the player
