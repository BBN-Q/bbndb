# from .auspex import define_entities as ausp_ent
# from .qgl import define_entities as qgl_ent
from . import qgl
from . import auspex
from . import calibration
from .session import Session, engine, Base, session_scope, cl_session, pl_session, get_cl_session, get_pl_session, initialize_db
from sqlalchemy import create_engine
from sqlalchemy.inspection import inspect
from sqlalchemy.orm import class_mapper
import sqlalchemy

def set_defaults_up_front(obj, args, kwargs):
    for key, col in sqlalchemy.inspect(obj.__class__).columns.items():
        if hasattr(col, 'default'):
            if col.default is not None:
                if callable(col.default.arg):
                    setattr(obj, key, col.default.arg(obj))
                else:
                    setattr(obj, key, col.default.arg)
mapper = sqlalchemy.orm.mapper
sqlalchemy.event.listen(mapper, 'init', set_defaults_up_front)

def copy_sqla_object(obj, omit_fk=True):
    """
    Given an SQLAlchemy object, creates a new object and copies
    across all attributes, omitting PKs, FKs (by default), and relationship
    attributes.

    Originally from Rudolf Cardinal: https://groups.google.com/forum/#!topic/sqlalchemy/wb2M_oYkQdY
    """
    cls = type(obj)
    mapper = class_mapper(cls)
    pk_keys = set([c.key for c in mapper.primary_key])
    rel_keys = set([c.key for c in mapper.relationships])
    prohibited = pk_keys | rel_keys
    if omit_fk:
        fk_keys = set([c.key for c in mapper.columns if c.foreign_keys])
        prohibited = prohibited | fk_keys
    # print("copy_sqla_object: skipping: {}".format(prohibited))
    to_set = {}
    for k in [p.key for p in mapper.iterate_properties if p.key not in prohibited]:
        try:
            value = getattr(obj, k)
            # print("copy_sqla_object: processing attribute {} = {}".format(k, value))
            to_set[k] = value
        except AttributeError:
            # print("copy_sqla_object: failed attribute {}".format(k))
            pass
    return cls(**to_set)

def deepcopy_sqla_object(startobj, session, flush=True):
    """
    Originally from Rudolf Cardinal: https://groups.google.com/forum/#!topic/sqlalchemy/wb2M_oYkQdY
    """
    objmap = {}  # keys = old objects, values = new objects
    # print("deepcopy_sqla_object: pass 1: create new objects")
    # Pass 1: iterate through all objects. (Can't guarantee to get
    # relationships correct until we've done this, since we don't know whether
    # or where the "root" of the PK tree is.)
    stack = [startobj]
    while stack:
        oldobj = stack.pop(0)
        if oldobj in objmap:  # already seen
            continue
        # print("deepcopy_sqla_object: copying {}".format(oldobj))
        newobj = copy_sqla_object(oldobj)
        # Don't insert the new object into the session here; it may trigger
        # an autoflush as the relationships are queried, and the new objects
        # are not ready for insertion yet (as their relationships aren't set).
        # Not also the session.no_autoflush option:
        # "sqlalchemy.exc.OperationalError: (raised as a result of Query-
        # invoked autoflush; consider using a session.no_autoflush block if
        # this flush is occurring prematurely)..."
        objmap[oldobj] = newobj
        insp = inspect(oldobj)
        for relationship in insp.mapper.relationships:
            # print("deepcopy_sqla_object: ... relationship: {}".format(
                # relationship))
            related = getattr(oldobj, relationship.key)
            if relationship.uselist:
                stack.extend(related)
            elif related is not None:
                stack.append(related)
    # Pass 2: set all relationship properties.
    # print("deepcopy_sqla_object: pass 2: set relationships")
    for oldobj, newobj in objmap.items():
        # print("deepcopy_sqla_object: newobj: {}".format(newobj))
        insp = inspect(oldobj)
        # insp.mapper.relationships is of type
        # sqlalchemy.utils._collections.ImmutableProperties, which is basically
        # a sort of AttrDict.
        for relationship in insp.mapper.relationships:
            # The relationship is an abstract object (so getting the
            # relationship from the old object and from the new, with e.g.
            # newrel = newinsp.mapper.relationships[oldrel.key],
            # yield the same object. All we need from it is the key name.
            # print("deepcopy_sqla_object: ... relationship: {}".format(
                # relationship.key))
            related_old = getattr(oldobj, relationship.key)
            if relationship.uselist:
                related_new = [objmap[r] for r in related_old]
            elif related_old is not None:
                related_new = objmap[related_old]
            else:
                related_new = None
            # print("deepcopy_sqla_object: ... ... adding: {}".format(
                # related_new))
            setattr(newobj, relationship.key, related_new)
    # Now we can do session insert.
    # print("deepcopy_sqla_object: pass 3: insert into session")
    for newobj in objmap.values():
        session.add(newobj)
    # Done
    # print("deepcopy_sqla_object: done")
    if flush:
        session.flush()
    return objmap[startobj]  # returns the new object matching startobj
