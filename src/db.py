from sqlalchemy import MetaData, Table, Column, Integer, String, Boolean, ForeignKey, DateTime,  create_engine

engine = create_engine('sqlite:///data.sqlite', echo=True, pool_size=20)
meta = MetaData()
History = Table(
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
  Column('docker_id', String, nullable=False),
)
AvailableInstances = Table(
  'available_instances', meta,
  Column('id', Integer, primary_key=True),
  Column('key', String, unique=True, nullable=False),
  Column('image_name', String, nullable=False),
  Column('config', String, nullable=False),
  Column('global', Boolean, nullable=False),
  Column('connstr', String, nullable=False),
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
meta.create_all(engine)
