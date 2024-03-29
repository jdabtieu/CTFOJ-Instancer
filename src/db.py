from sqlalchemy import MetaData, Table, Column, Integer, String, Boolean, ForeignKey, DateTime,  create_engine


class InstanceStatus:
  RUNNING = 1
  STOPPING = 2
  STOPPED = 0


engine = create_engine('sqlite:///data.sqlite', pool_size=20)
meta = MetaData()
History = Table(
  'history', meta,
  Column('id', Integer, primary_key=True),
  Column('instance', ForeignKey('images.id'), nullable=False),
  Column('player', Integer, nullable=False),
  Column('token', ForeignKey('tokens.id'), nullable=False),
  Column('request_time', DateTime, nullable=False),
  Column('expiry_time', DateTime, nullable=False),
  Column('status', Integer, nullable=False, default=InstanceStatus.RUNNING),
  Column('flag', String, nullable=False),
  Column('host', String, nullable=False),
  Column('port', Integer, nullable=False),
  Column('docker_id', String, nullable=False),
)
Images = Table(
  'images', meta,
  Column('id', Integer, primary_key=True),
  Column('key', String, unique=True, nullable=False),
  Column('image_name', String, nullable=False),
  Column('config', String, nullable=False),
  Column('is_global', Boolean, nullable=False),
  Column('connstr', String, nullable=False),
  Column('duration', Integer, nullable=False),
)
Users = Table(
  'users', meta,
  Column('id', Integer, primary_key=True),
  Column('username', String, unique=True, nullable=False),
  Column('password', String, nullable=False),
)
Tokens = Table(
  'tokens', meta,
  Column('id', Integer, primary_key=True),
  Column('name', String, nullable=False),
  Column('key', String, nullable=False),
)
