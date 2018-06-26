# from .auspex import define_entities as ausp_ent
# from .qgl import define_entities as qgl_ent
from . import qgl
from . import auspex

def define_entities(db):
	auspex.define_entities(db)
	qgl.define_entities(db)