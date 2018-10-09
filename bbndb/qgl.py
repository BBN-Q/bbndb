'''
Channels is where we store information for mapping virtual (qubit) channel to real channels.

Created on Jan 19, 2012 in the QGL package

Original Author: Colm Ryan
Modified By: Graham Rowlands (moved to bbndb and ported to ORM)

Copyright 2013 Raytheon BBN Technologies

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
'''

import numpy as np
from math import tan, cos, pi
from copy import deepcopy
import datetime

from sqlalchemy import Column, DateTime, String, Boolean, Float, Integer, LargeBinary, ForeignKey, func, JSON, PickleType
from sqlalchemy.orm import relationship, backref, validates
from sqlalchemy.ext.declarative import declared_attr

from session import Base, Session, engine

class DatabaseItem(object):
    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()
    @declared_attr
    def channel_db_id(cls):
        return Column(Integer, ForeignKey('channeldatabase.id'))

    id    = Column(Integer, primary_key=True)
    label = Column(String, nullable=False)

    def __repr__(self):
        return str(self)
    def __str__(self):
        return f"{self.__class__.__name__}('{self.label}')"

class ChannelDatabase(Base):
    __tablename__ = "channeldatabase"
    id = Column(Integer, primary_key=True)

    label        = Column(String, nullable=False)
    time         = Column(DateTime)

    channels     = relationship("Channel", backref="channel_db", cascade="all, delete, delete-orphan")
    sources      = relationship("Generator", backref="channel_db", cascade="all, delete, delete-orphan")
    transmitters = relationship("Transmitter", backref="channel_db", cascade="all, delete, delete-orphan")
    receivers    = relationship("Receiver", backref="channel_db", cascade="all, delete, delete-orphan")
    transceivers = relationship("Transceiver", backref="channel_db", cascade="all, delete, delete-orphan")
    instruments  = relationship("Instrument", backref="channel_db", cascade="all, delete, delete-orphan")
    processors   = relationship("Processor", backref="channel_db", cascade="all, delete, delete-orphan")
    
    def __repr__(self):
        return str(self)
    def __str__(self):
        return f"ChannelDatabase(id={self.id}, label={self.label})"

class Instrument(DatabaseItem, Base):
    model      = Column(String, nullable=False)
    address    = Column(String)
    parameters = Column(PickleType, default={}, nullable=False)
    
class Generator(DatabaseItem, Base):
    model            = Column(String, nullable=False)
    address          = Column(String)
    power            = Column(Float, nullable=False)
    frequency        = Column(Float, nullable=False)

    physicalchannels = relationship("PhysicalChannel", back_populates="generator")
    
class Receiver(DatabaseItem, Base):
    """A receiver , or generally an analog to digitial converter"""
    model            = Column(String, nullable=False)
    address          = Column(String)
    stream_types     = Column(String, default="raw", nullable=False)
    trigger_source   = Column(String, default="external", nullable=False)
    record_length    = Column(Integer, default=1024, nullable=False)
    sampling_rate    = Column(Float, default=1e9, nullable=False)
    number_segments  = Column(Integer, default=1) # This should be automati, nullable=Falsec
    number_waveforms = Column(Integer, default=1) # This should be automati, nullable=Falsec
    number_averages  = Column(Integer, default=100) # This should be automati, nullable=Falsec
    transceiver_id   = Column(Integer, ForeignKey("transceiver.id"))
    acquire_mode     = Column(String, default="digitizer", nullable=False)

    channels = relationship("ReceiverChannel", back_populates="receiver", cascade="all, delete, delete-orphan")

    @validates('acquire_mode')
    def validate_acquire_mode(self, key, source):
        assert source in ['digitizer ', 'averager']
        return source
    
    @validates('trigger_source')
    def validate_trigger_source(self, key, source):
        assert source in ['external', 'internal']
        return source
    # def get_chan(self, name):
    #     return self.channels.select(lambda x: x.label.endswith(name)).first()
    # def ch(self, name):
    #     return self.get_chan(name)
    #     def __getitem__(self, value):
    #     return self.get_chan(value)

class Transmitter(DatabaseItem, Base):
    """An arbitrary waveform generator, or generally a digital to analog converter"""
    model            = Column(String, nullable=False)
    address          = Column(String)
    trigger_interval = Column(Float, default=100e-6, nullable=False)
    trigger_source   = Column(String, default="external", nullable=False)
    delay            = Column(Float, default=0.0, nullable=False)
    master           = Column(Boolean, default=False, nullable=False)
    sequence_file    = Column(String)
    transceiver_id   = Column(Integer, ForeignKey("transceiver.id"))
    
    channels = relationship("PhysicalChannel", back_populates="transmitter", cascade="all, delete, delete-orphan")

    @validates('trigger_source')
    def validate_trigger_source(self, key, source):
        assert source in ['external', 'internal']
        return source
    
    # def get_chan(self, name):
    #     return self.channels.select(lambda x: x.label.endswith(name)).first()
    # def ch(self, name):
    #     return self.get_chan(name)
    # def __getitem__(self, value):
        # return self.get_chan(value)

class Processor(DatabaseItem, Base):
    """A hardware unit used for signal processing, e.g. a TDM"""
    model          = Column(String, nullable=False)
    address        = Column(String)
    transceiver_id = Column(Integer, ForeignKey("transceiver.id"))

class Transceiver(DatabaseItem, Base):
    """A single machine or rack of a2ds and d2as that we want to treat as a unit."""
    model        = Column(String, nullable=False)
    master       = Column(String)

    receivers    = relationship("Receiver", backref="transceiver")
    transmitters = relationship("Transmitter", backref="transceiver")
    processors   = relationship("Processor", backref="transceiver")

    # def get_transmitter(self, name):
    #     return self.transmitters.select(lambda x: x.label.endswith(name)).first()
    # def get_receiver(self, name):
    #     return self.receivers.select(lambda x: x.label.endswith(name)).first()

class Channel(Base):
    '''
    Every channel has a label and some printers.
    '''
    __tablename__ = "channel"
    id            = Column(Integer, primary_key=True)
    type          = Column(String(50))
    label         = Column(String, nullable=False)
    channel_db_id = Column(Integer, ForeignKey('channeldatabase.id'))

    __mapper_args__ = {
        'polymorphic_identity':'channel',
        'polymorphic_on':type
    }
    # def __setattr__(self, attr, value):
    #     if cache_callback:
    #         if attr in [a.name for a in self._attrs_]:
    #             cache_callback()
    #     super(Channel, self).__setattr__(attr, value)

class ChannelMixin(object):
    # Omit the __tablename__ so that all channels occupy the same table
    # @declared_attr
    # def channel_db_id(cls):
    #     return Column(Integer, ForeignKey('channeldatabase.id'))
    @declared_attr
    def id(cls):
        return Column(Integer, ForeignKey("channel.id"), primary_key=True)
    @declared_attr
    def __mapper_args__(cls):
        return {'polymorphic_identity': cls.__name__.lower()}
    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()

    def __repr__(self):
        return str(self)
    def __str__(self):
        return f"{self.__class__.__name__}('{self.label}')"

class PhysicalChannel(ChannelMixin, Channel):
    '''
    The main class for actual Transmitter channels.
    '''
    instrument      = Column(String) # i.e. the Transmitter or receiver
    translator      = Column(String)
    sampling_rate   = Column(Float, default=1.2e9, nullable=False)
    delay           = Column(Float, default=0.0, nullable=False)

    generator_id    = Column(Integer, ForeignKey("generator.id"))
    generator       = relationship("Generator", back_populates="physicalchannels")

    logicalchannel_id = Column(Integer, ForeignKey("logicalchannel.id"))
    
    transmitter_id  = Column(Integer, ForeignKey("transmitter.id"))
    transmitter     = relationship("Transmitter", back_populates="channels")

    # def q(self):
        # if isinstance(self.logical_channel, Qubit):
            # return self.logical_channel

class LogicalChannel(ChannelMixin, Channel):
    '''
    The main class from which we will generate sequences.
    At some point it needs to be assigned to a physical channel.
        frequency: modulation frequency of the channel (can be positive or negative)
    '''
    frequency    = Column(Float, default=0.0, nullable=False)
    pulse_params = Column(PickleType, default={})

    physicalchannel = relationship("PhysicalChannel", uselist=False, backref="logicalchannel", 
                                   foreign_keys="[PhysicalChannel.logicalchannel_id]")

class PhysicalMarkerChannel(PhysicalChannel, ChannelMixin):
    '''
    A digital output channel on an Transmitter.
        gate_buffer: How much extra time should be added onto the beginning of a gating pulse
        gate_min_width: The minimum marker pulse width
    '''
    id = Column(Integer, ForeignKey("physicalchannel.id"), primary_key=True)

    gate_buffer    = Column(Float, default=0.0, nullable=False)
    gate_min_width = Column(Float, default=0.0, nullable=False)

class PhysicalQuadratureChannel(PhysicalChannel, ChannelMixin):
    '''
    Something used to implement a standard qubit channel with two analog channels and a microwave gating channel.
    '''
    id = Column(Integer, ForeignKey("physicalchannel.id"), primary_key=True)

    amp_factor           = Column(Float, default=1.0, nullable=False)
    phase_skew           = Column(Float, default=0.0, nullable=False)
    I_channel_offset     = Column(Float, default=0.0, nullable=False)
    Q_channel_offset     = Column(Float, default=0.0, nullable=False)
    I_channel_amp_factor = Column(Float, default=1.0, nullable=False)
    Q_channel_amp_factor = Column(Float, default=1.0, nullable=False)

class ReceiverChannel(PhysicalChannel, ChannelMixin):
    '''
    A trigger input on a receiver.
    '''
    id = Column(Integer, ForeignKey("physicalchannel.id"), primary_key=True)

    channel            = Column(Integer, nullable=False)
    dsp_channel        = Column(Integer)
    stream_type        = Column(String, default="raw", nullable=False)
    if_freq            = Column(Float, default=0.0, nullable=False)
    kernel             = Column(LargeBinary) # Float64 byte representation of kernel
    kernel_bias        = Column(Float, default=0.0, nullable=False)
    threshold          = Column(Float, default=0.0, nullable=False)
    threshold_invert   = Column(Boolean, default=False, nullable=False)

    receiver_id        = Column(Integer, ForeignKey("receiver.id"))
    receiver           = relationship("Receiver", back_populates="channels")

    triggering_chan_id = Column(Integer, ForeignKey("measurement.id"))

    def pulse_check(name):
        return name in ["constant", "gaussian", "drag", "gaussOn", "gaussOff", "dragGaussOn", "dragGaussOff",
                       "tanh", "exp_decay", "autodyne", "arb_axis_drag"]

    @validates('stream_type')
    def validate_stream_type(self, key, source):
        assert source in ["raw", "demodulated", "integrated", "averaged"]
        return source

class LogicalMarkerChannel(LogicalChannel, ChannelMixin):
    '''
    A class for digital channels for gating sources or triggering other things.
    '''
    id = Column(Integer, ForeignKey("logicalchannel.id"), primary_key=True)
    
    meas_chan_id = Column(Integer, ForeignKey("measurement.id"))
    meas_gate_id = Column(Integer, ForeignKey("measurement.id"))

    def __init__(self, **kwargs):
        if "pulse_params" not in kwargs.keys():
            kwargs["pulse_params"] =  {'shape_fun': "constant",'length': 10e-9}
        super(LogicalMarkerChannel, self).__init__(**kwargs)

class Qubit(LogicalChannel, ChannelMixin):
    '''
    The main class for generating qubit pulses.  Effectively a logical "QuadratureChannel".
        frequency: modulation frequency of the channel (can be positive or negative)
    '''
    id = Column(Integer, ForeignKey("logicalchannel.id"), primary_key=True)

    edge_source_id = Column(Integer, ForeignKey("edge.id"))
    edge_target_id = Column(Integer, ForeignKey("edge.id"))

    def __init__(self, **kwargs):
        if "pulse_params" not in kwargs.keys():
            kwargs["pulse_params"] =  {'length': 20e-9,
                            'piAmp': 1.0,
                            'pi2Amp': 0.5,
                            'shape_fun': "gaussian",
                            'cutoff': 2,
                            'drag_scaling': 0,
                            'sigma': 5e-9}
        super(Qubit, self).__init__(**kwargs)

class Measurement(LogicalChannel, ChannelMixin):
    '''
    A class for measurement channels.
    Measurements are special because they can be different types:
    autodyne which needs an IQ pair or hetero/homodyne which needs just a marker channel.
        meas_type: Type of measurement (autodyne, homodyne)
        autodyne_freq: use to bake the modulation into the pulse, so that it has constant phase
        frequency: use to asssociate modulation with the channel
    '''
    id = Column(Integer, ForeignKey("logicalchannel.id"), primary_key=True)

    meas_type     = Column(String, default='autodyne', nullable=False)
    autodyne_freq = Column(Float, default=0.0, nullable=False)

    trig_chan     = relationship("LogicalMarkerChannel", uselist=False, backref="meas_chan", foreign_keys="[LogicalMarkerChannel.meas_chan_id]")
    gate_chan     = relationship("LogicalMarkerChannel", uselist=False, backref="trig_meas", foreign_keys="[LogicalMarkerChannel.meas_gate_id]")
    receiver_chan = relationship("ReceiverChannel", uselist=False, backref="triggering_chan", foreign_keys="[ReceiverChannel.triggering_chan_id]")

    @validates('meas_type')
    def validate_meas_type(self, key, source):
        assert source in ['autodyne', 'homodyne']
        return source
    
    def __init__(self, **kwargs):
        if "pulse_params" not in kwargs.keys():
            kwargs["pulse_params"] =  {'length': 100e-9,
                                'amp': 1.0,
                                'shape_fun': "tanh",
                                'cutoff': 2,
                                'sigma': 1e-9}
        super(Measurement, self).__init__(**kwargs)

class Edge(LogicalChannel, ChannelMixin):
    '''
    Defines an arc/directed edge between qubit vertices. If a device supports bi-directional
    connectivity, that is represented with two independent Edges.

    An Edge is also effectively an abstract channel, so it carries the same properties as a
    Qubit channel.
    '''
    id = Column(Integer, ForeignKey("logicalchannel.id"), primary_key=True)

    source = relationship("Qubit", uselist=False, backref="edge_source", foreign_keys="[Qubit.edge_source_id]")
    target = relationship("Qubit", uselist=False, backref="edge_target", foreign_keys="[Qubit.edge_target_id]")

    def __init__(self, **kwargs):
        if "pulse_params" not in kwargs.keys():
            kwargs["pulse_params"] =   {'length': 20e-9,
                                        'amp': 1.0,
                                        'phase': 0.0,
                                        'shape_fun': "gaussian",
                                        'cutoff': 2,
                                        'drag_scaling': 0,
                                        'sigma': 5e-9,
                                        'riseFall': 20e-9}
        super(Edge, self).__init__(**kwargs)

if __name__ == '__main__':
    
    from sqlalchemy import create_engine
    engine = create_engine('sqlite:///:memory:', echo=True)
    Base.metadata.create_all(engine)

    # from sqlalchemy.orm import sessionmaker
    # Session = sessionmaker(bind=engine)
    Session.configure(bind=engine)
    session = Session()

    q1 = Qubit(label="q1")
    q2 = Qubit(label="q2")
    e1 = Edge(label="e1", source=q1, target=q2)
    session.add_all([q1,q2,e1])

    b = ChannelDatabase(label="working2")
    s = Generator(label="Src1", model="abc", power=10.0, frequency=5.0e9)
    b.sources.append(s)
    session.add_all([b,s])
    session.new
    session.commit()





