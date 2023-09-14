FROM ubuntu AS app

FROM pwn.red/jail
COPY --from=app / /srv
COPY script.sh /srv/app/run
