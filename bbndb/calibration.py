import numpy as np
from copy import deepcopy
import datetime

from sqlalchemy import Column, DateTime, String, Boolean, Float, Integer, ForeignKey
from sqlalchemy.orm import relationship, backref
from . import session 

class Sample(session.Base):
    __tablename__ = "sample"
    id           = Column(Integer, primary_key=True)
    name         = Column(String, nullable=False)
    calibrations = relationship("Calibration", backref="sample")

class Calibration(session.Base):
    __tablename__ = "calibration"
    id          = Column(Integer, primary_key=True)
    name        = Column(String, nullable=False) # e.g. T2, or Pi2Amp
    category    = Column(String) # e.g. Rabi, PhaseCal, etc. to distinguish between multiple cal types for same parameter
    value       = Column(Float, nullable=False)
    uncertainty = Column(Float)
    date        = Column(DateTime)
    sample_id   = Column(Integer, ForeignKey("sample.id"))
