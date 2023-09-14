# Shell Script
A simple example showing a nc challenge running a shell script that prints the flag to stdout.

In general, when using [redpwn jail](sudo docker build -t ctfhelloworld .) (recommended for
most pwn challenges), the flag will be stored in the `FLAG` environment variable by
CTFOJ-Instancer.

To build and tag this example, run:
```
sudo docker build -t yourtaghere .
```
Whatever you set the tag as, you must specify it when creating an image in the
admin interface as 'Docker Image Name'
