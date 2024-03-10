import docker
from datetime import datetime
import time
from sqlalchemy import func, update, insert, select
import sys
import signal

from db import engine, History, InstanceStatus


# Graceful shutdown
signalled = False
def handle_sighup(signum, frame):
    global signalled
    signalled = True
signal.signal(signal.SIGHUP, handle_sighup)


def actually_destroy_instance(container_id):
  # Get the image spec
  conn = engine.connect()
  instance = conn.execute(
    History.select().where(
      History.c.docker_id == container_id,
    )
  ).fetchone()
  if instance is None:
    conn.close()
    return "This instance does not exist"
  # Get the running instance's Docker data
  client = docker.from_env()
  try:
    container = client.containers.get(instance.docker_id)
  except docker.errors.NotFound:
    # Something bad must have happened, might as well clear it
    conn.execute(
      update(History).
      where(History.c.id == instance.id).
      values(status=InstanceStatus.STOPPED)
    )
    conn.commit()
    conn.close()
    return ""
  
  # Kill the container and update the stop time
  container.remove(force=True)
  conn.execute(
    update(History).
    where(History.c.id == instance.id).
    values(status=InstanceStatus.STOPPED)
  )
  conn.commit()
  conn.close()
  return ""

def main():
    while not signalled:
      conn = engine.connect()
      # Find queued jobs
      to_stop = conn.execute(
        History.select().where(
          History.c.expiry_time <= datetime.now(),
          History.c.status == InstanceStatus.RUNNING
        )
      ).fetchall()

      # Set them to pending
      conn.execute(
        update(History).
        where(History.c.id.in_([x.id for x in to_stop])).
        values(status=InstanceStatus.STOPPING)
      )
      conn.commit()
      conn.close()

      # And now go stop them
      for container in to_stop:
        r = actually_destroy_instance(container.docker_id)
        if r:
          sys.stderr.write(f"error while stopping {container.docker_id}: {r}\n")
      time.sleep(5)


if __name__ == "__main__":
  main()
