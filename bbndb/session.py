from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# configure Session to be used by all importers
Session = sessionmaker()

# engine to be used by all importers
engine = None

# The base class for sqlalchemy ORM
Base = declarative_base()