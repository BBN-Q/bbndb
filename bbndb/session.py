from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from contextlib import contextmanager

# configure Session to be used by all importers
Session = sessionmaker()

# Actual current session
session = None

# engine to be used by all importers
engine = None

# The base class for sqlalchemy ORM
Base = declarative_base()

@contextmanager
def session_scope():
    """Provide a transactional scope around a series of operations."""
    session = Session()
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()