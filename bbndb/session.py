from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.pool import StaticPool
from sqlalchemy import create_engine

import alembic as al
from alembic.config import Config as AlembicConfig
from alembic.script import ScriptDirectory

from contextlib import contextmanager
import os

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
        # print("Creating engine...")
        engine = create_engine(provider, connect_args={'check_same_thread':False},
                                     poolclass=StaticPool, echo=False)

        Base.metadata.create_all(engine)
        Session.configure(bind=engine)

        acfg = AlembicConfig(os.path.join(os.path.dirname(__file__), "../alembic.ini"))
        acfg.set_main_option("sqlalchemy.url", provider)

        if ":memory:" not in provider:

            script = ScriptDirectory.from_config(acfg)
            heads  = script.get_revisions("heads")
            if len(heads) > 1:
                logger.warning("More than one database version possibility found... this is weird...")
            bbndb_rev = heads[0].revision

            # Horrible monkey-patch to get the current revision:
            rev = None
            def print_stdout(text, *arg):
                nonlocal rev
                rev = text.split()[0]
            acfg.print_stdout = print_stdout

            # Get the current revision
            al.command.current(acfg)
            # Stamp it with current revision if it's None
            if rev is None:
                al.command.stamp(acfg, bbndb_rev)
            # Check to see if we have a version mismatch
            # In the future, we might perform the upgrade for you.
            elif bbndb_rev != rev:
                print(f"Revision of the requested database {provider}: {rev} does not match the current bbndb revision: {bbndb_rev}\
                    Please migrate the database to the current version or recreate the database. The former can be done using\
                    the alembic command line tools. See alembic/README.md in the bbndb directory for details.")

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

