from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.pool import StaticPool
from sqlalchemy import create_engine

from contextlib import contextmanager

# configure Session to be used by all importers
Session = sessionmaker()

# Actual current sessions
cl_session = None # Channel Library
pl_session = None # Pipeline

# engine to be used by all importers
engine = None

# The base class for sqlalchemy ORM
Base = declarative_base()

# For getting everything started
def initialize_db(provider):
    global engine, Session, Base
    if not engine:
        print("Creating engine...")
        engine = create_engine(provider, connect_args={'check_same_thread':False},
                                     poolclass=StaticPool, echo=False)
        Base.metadata.create_all(engine)
        Session.configure(bind=engine)

def get_cl_session():
    global Session, cl_session
    if not cl_session:
        cl_session = Session()
    return cl_session

def get_pl_session():
    global Session, pl_session
    if not pl_session:
        pl_session = Session()
    return pl_session

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

