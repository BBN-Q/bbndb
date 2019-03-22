import numpy as np
from copy import deepcopy
import datetime

from sqlalchemy import Column, DateTime, String, Boolean, Float, Integer, LargeBinary, ForeignKey, func, JSON, PickleType
from sqlalchemy.orm import relationship, backref, validates
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy import inspect
from IPython.display import HTML, display
from . import session #session.Base, Session, engine

class Sample(session.Base):
    __tablename__ = "sample"
    id        = Column(Integer, primary_key=True)
    name      = Column(String, nullable=False)
    calibrations       = relationship("Calibration", backref="sample")
    T2s       = relationship("T2", backref="sample")
    T2stars   = relationship("T2", backref="sample")

class Calibration(session.Base):
    __tablename__ = "t1"
    id          = Column(Integer, primary_key=True)
    name        = Column(String, nullable=False) # e.g. T2, or Pi2Amp
    value       = Column(Float, nullable=False)
    uncertainty = Column(Float, nullable=False)
    date        = Column(DateTime)
