# Python
A simple example showing a nc challenge running a Python script that prints the flag to stdout after a user prompt.

In general, when using [redpwn jail](https://github.com/redpwn/jail) (recommended for
most pwn challenges), the flag will be stored in the `FLAG` environment variable by
CTFOJ-Instancer.

To build and tag this example, run:
```
sudo docker build -t yourtaghere .
```
Whatever you set the tag as, you must specify it when creating an image in the
admin interface as 'Docker Image Name'

## Python-Specific Notes
When using Python with redpwn jail, there are a few things to keep in mind:
1. Try and use a slim Python image, such as `python:slim` or `python:3.11-alpine` if possible
2. The Dockerfile should specify a memory limit of at least 10MB (`ENV JAIL_MEM=10M`), otherwise the Python script may fail
to start (upon connecting with nc, you'll see no input or output). This figure of 10MB can be adjusted as necessary, but if
upon connecting via `nc`, nothing appears to happen, not enough memory is probably why.
4. The Python script must be marked as executable (`chmod +x main.py`) and contain this as the first line: `#!/usr/local/bin/python`)
