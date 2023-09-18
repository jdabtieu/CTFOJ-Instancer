# CTFOJ-Instancer
Instancer for secure CTF challenges hosted with CTFOJ

## Preface (A Warning)
**CTFOJ-Instancer is currently in <ins>alpha</ins>. Nice-to-have features are missing, challenges cannot be edited/deleted without messing with the database, and you need to ssh to build Docker containers.**
If you are dedicated enough, it is serviceable, but we are in the process of making it significantly easier to use.

## Installation
CTFOJ-Instancer is a **Linux-only (ideally Ubuntu/Debian)** web app, and to start using it:
- Install Docker (and optionally, docker-compose)
- Grant the web daemon user the `docker` group with `sudo usermod -aG docker username`. Because this is a powerful command, it is recommended to use a dedicated user for CTFOJ-Instancer, and not `www-data` or similar
- Ensure python3 is installed and the dependencies are installed (`pip3 install -r requirements.txt` in the `src/` folder)
- Run `install.py`
- Run it as a web server (ideally, port 443) and make it available at some public IP/domain=
  - Use a WSGI server to point to application.py
  - Ideally proxy that through nginx
- Ensure ports 443 and 32768+ are not blocked by a firewall. 443 (https) is used for the management panel, and ports 32768+ are for challenge instances

## Setting up instances
- Build and tag a Docker image corresponding to your challenge on the CTFOJ-Instancer server
- In CTFOJ, check the box for instancing when creating/editing a problem
- Copy the instancer key and in CTFOJ-Instancer, use it to create an instance along with the Docker image tag
- If done correctly, on CTFOJ, the problem will display a box to deploy and instance, and when you click create instance, an instance is created

## API Documentation
While instances will be managed by CTFOJ, you can do manual testing on the instancer API. Check out [the wiki](https://github.com/jdabtieu/CTFOJ-Instancer/wiki/Public-API-Documentation) for details.
