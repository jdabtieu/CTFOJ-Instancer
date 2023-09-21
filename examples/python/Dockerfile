FROM python:3.11-alpine AS app
FROM pwn.red/jail

COPY --from=app / /srv

COPY main.py /srv/app/run

ENV JAIL_TIME=60
ENV JAIL_MEM=10M
