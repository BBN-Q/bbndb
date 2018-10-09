# from .auspex import define_entities as ausp_ent
# from .qgl import define_entities as qgl_ent
from . import qgl
from . import auspex
from .session import Session, engine, Base, session_scope
from sqlalchemy import create_engine
