'''
Channels is where we store information for mapping virtual (qubit) channel to real channels.

Created on Jan 19, 2012 in the QGL package

Original Author: Colm Ryan
Modified By: Graham Rowlands (moved to bbndb using sqlalchemy)

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

from sqlalchemy import Column, DateTime, String, Boolean, Float, Integer, LargeBinary, ForeignKey, func, PickleType
from sqlalchemy.ext.mutable import Mutable
from sqlalchemy.orm import relationship, backref, validates
from sqlalchemy.ext.declarative import declared_attr

from .session import Base

class MutableDict(Mutable, dict):
    @classmethod
    def coerce(cls, key, value):
        if not isinstance(value, MutableDict):
            if isinstance(value, dict):
                return MutableDict(value)
            return Mutable.coerce(key, value)
        else:
            return value
    def __delitem(self, key):
        dict.__delitem__(self, key)
        self.changed()
    def __setitem__(self, key, value):
        dict.__setitem__(self, key, value)
        self.changed()
    def __getstate__(self):
        return dict(self)
    def __setstate__(self, state):
        self.update(self)

class DatabaseItem(object):
    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()
    @declared_attr
    def channel_db_id(cls):
        return Column(Integer, ForeignKey('channeldatabase.id'))

    id         = Column(Integer, primary_key=True)
    label      = Column(String, nullable=False)
    standalone = Column(Boolean, nullable=False, default=False)

    def __repr__(self):
        return str(self)
    def __str__(self):
        return f"{self.__class__.__name__}('{self.label}')"

class ChannelDatabase(Base):
    __tablename__ = "channeldatabase"
    id = Column(Integer, primary_key=True)

    label        = Column(String, nullable=False)
    time         = Column(DateTime)

    channels           = relationship("Channel", backref="channel_db", cascade="all, delete, delete-orphan")
    generators         = relationship("Generator", backref="channel_db", cascade="all, delete, delete-orphan")
    transmitters       = relationship("Transmitter", backref="channel_db", cascade="all, delete, delete-orphan")
    receivers          = relationship("Receiver", backref="channel_db", cascade="all, delete, delete-orphan")
    transceivers       = relationship("Transceiver", backref="channel_db", cascade="all, delete, delete-orphan")
    instruments        = relationship("Instrument", backref="channel_db", cascade="all, delete, delete-orphan")
    processors         = relationship("Processor", backref="channel_db", cascade="all, delete, delete-orphan")
    attenuators        = relationship("Attenuator", backref="channel_db", cascade="all, delete, delete-orphan")
    DCSources          = relationship("DCSource", backref="channel_db", cascade="all, delete, delete-orphan")
    spectrum_analyzers = relationship("SpectrumAnalyzer", backref='channel_db', cascade='all, delete, delete-orphan')

    def all_instruments(self):
        return self.generators + self.transmitters + self.receivers + self.transceivers + self.instruments + self.processors + self.attenuators + self.DCSources + self.spectrum_analyzers
    def __repr__(self):
        return str(self)
    def __str__(self):
        return f"ChannelDatabase(id={self.id}, label={self.label})"

class Instrument(DatabaseItem, Base):
    model      = Column(String, nullable=False)
    address    = Column(String)
    parameters = Column(MutableDict.as_mutable(PickleType), default={}, nullable=False)

class Attenuator(DatabaseItem, Base):
    model    = Column(String, nullable=False)
    address  = Column(String)

    channels = relationship("AttenuatorChannel", back_populates="attenuator", cascade="all, delete, delete-orphan")

    def get_chan(self, name):
        if isinstance(name, int):
            name = f"-{name}"
        matches = [c for c in self.channels if c.label.endswith(name)]
        if len(matches) == 0:
            raise ValueError(f"Could not find a channel name on attenuator {self.label} ending with {name}")
        elif len(matches) > 1:
            raise ValueError(f"Found {len(matches)} matches for channels on attenuator {self.label} whose names end with {name}")
        else:
            return matches[0]
    def ch(self, name):
        return self.get_chan(name)
    def __getitem__(self, value):
        return self.get_chan(value)

class Generator(DatabaseItem, Base):
    model            = Column(String, nullable=False)
    address          = Column(String)
    power            = Column(Float, nullable=False)
    frequency        = Column(Float, nullable=False)
    reference        = Column(String)

    spectrumanalyzer_id = Column(Integer, ForeignKey("spectrumanalyzer.id"))
    DCsource_id = Column(Integer, ForeignKey('dcsource.id'))

    phys_chans = relationship("PhysicalChannel", back_populates="generator")

class SpectrumAnalyzer(DatabaseItem, Base):
    model     = Column(String, nullable=False)
    address   = Column(String)
    LO_source = relationship("Generator", uselist=False, foreign_keys="[Generator.spectrumanalyzer_id]")
    phys_chans   = relationship("PhysicalChannel", back_populates = 'spectrumanalyzer')

class DCSource(DatabaseItem, Base):
    model     = Column(String, nullable=False)
    address   = Column(String)
    output    = Column(Boolean, default=False)
    level     = Column(Float, default=0)
    mode      = Column(String, default='current')
    pump_source = relationship("Generator", uselist=False, foreign_keys="[Generator.DCsource_id]")
    phys_chans  = relationship('PhysicalChannel', back_populates = 'DCsource')

class Receiver(DatabaseItem, Base):
    """A receiver , or generally an analog to digitial converter"""
    model            = Column(String, nullable=False)
    address          = Column(String)
    stream_types     = Column(String, default="raw", nullable=False)
    trigger_source   = Column(String, default="external", nullable=False)
    record_length    = Column(Integer, default=1024, nullable=False)
    sampling_rate    = Column(Float, default=1e9, nullable=False)
    vertical_scale   = Column(Float, default=1.0, nullable=False)
    number_segments  = Column(Integer, default=1) # This should be automati, nullable=Falsec
    number_waveforms = Column(Integer, default=1) # This should be automati, nullable=Falsec
    number_averages  = Column(Integer, default=100) # This should be automati, nullable=Falsec
    transceiver_id   = Column(Integer, ForeignKey("transceiver.id"))
    acquire_mode     = Column(String, default="digitizer", nullable=False)
    reference        = Column(String, default="external")
    stream_sel       = Column(String, nullable = False)
    channels = relationship("PhysicalChannel", back_populates="receiver", cascade="all, delete, delete-orphan")

    @validates('acquire_mode')
    def validate_acquire_mode(self, key, source):
        assert source in ['digitizer', 'averager']
        return source

    @validates('reference')
    def validate_reference(self, key, source):
        assert source in ['external', 'internal']
        return source

    @validates('trigger_source')
    def validate_trigger_source(self, key, source):
        assert source in ['external', 'internal']
        return source

    def get_chan(self, name):
        if isinstance(name, int):
            name = f"-{name}"
        matches = [c for c in self.channels if c.label.endswith(name)]
        if len(matches) == 0:
            raise ValueError(f"Could not find a channel name on receiver {self.label} ending with {name}")
        elif len(matches) > 1:
            raise ValueError(f"Found {len(matches)} matches for channels on receiver {self.label} whose names end with {name}")
        else:
            return matches[0]
    def ch(self, name):
        return self.get_chan(name)
    def __getitem__(self, value):
        return self.get_chan(value)

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
        assert source in ['external', 'internal', 'system']
        return source
    def get_chan(self, name):
        if isinstance(name, int):
            name = f"-{name}"
        matches = [c for c in self.channels if c.label.endswith(name)]
        if len(matches) == 0:
            raise ValueError(f"Could not find a channel name on transmitter {self.label} ending with {name}")
        elif len(matches) > 1:
            raise ValueError(f"Found {len(matches)} matches for channels on transmitter {self.label} whose names end with {name}")
        else:
            return matches[0]
    def ch(self, name):
        return self.get_chan(name)
    def __getitem__(self, value):
        return self.get_chan(value)
    # def get_chan(self, name):
    #     return self.channels.select(lambda x: x.label.endswith(name)).first()
    # def ch(self, name):
    #     return self.get_chan(name)
    # def __getitem__(self, value):
        # return self.get_chan(value)

class Processor(DatabaseItem, Base):
    """A hardware unit used for signal processing, e.g. a TDM"""
    model            = Column(String, nullable=False)
    address          = Column(String)
    transceiver_id   = Column(Integer, ForeignKey("transceiver.id"))
    master           = Column(Boolean, default=False, nullable=False)
    trigger_interval = Column(Float, default=100e-6, nullable=False)
    trigger_source   = Column(String, default="internal", nullable=False)

class Transceiver(DatabaseItem, Base):
    """A single machine or rack of a2ds and d2as that we want to treat as a unit."""
    model        = Column(String, nullable=False)
    master       = Column(String)
    address      = Column(String,nullable=False)
    initialize_separately = Column(Boolean, default=True, nullable=False)
    receivers    = relationship("Receiver", backref="transceiver")
    transmitters = relationship("Transmitter", backref="transceiver")
    processors   = relationship("Processor", backref="transceiver")

    def tx(self, name):
        return self.get_thing("transmitters", name)

    def rx(self, name):
        return self.get_thing("receviers", name)

    def px(self, name):
        return self.get_thing("processors", name)

    def get_thing(self, thing_type, name):
        if isinstance(name, int):
            name = f"_U{name}"
        matches = [c for c in getattr(self, thing_type) if c.label.endswith(name)]
        if len(matches) == 0:
            raise ValueError(f"Could not find a {thing_type} name on transceiver {self.label} ending with {name}")
        elif len(matches) > 1:
            raise ValueError(f"Found {len(matches)} matches for {thing_type} on transceiver {self.label} whose names end with {name}")
        else:
            return matches[0]

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

class ChannelMixin(object):
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
    instrument          = Column(String) # i.e. the Transmitter or receiver
    translator          = Column(String)
    sampling_rate       = Column(Float, default=1.2e9, nullable=False)
    delay               = Column(Float, default=0.0, nullable=False)

    generator_id        = Column(Integer, ForeignKey("generator.id"))
    generator           = relationship("Generator", back_populates="phys_chans")

    spectrumanalyzer_id = Column(Integer, ForeignKey("spectrumanalyzer.id"))
    spectrumanalyzer    = relationship("SpectrumAnalyzer", back_populates="phys_chans")

    DCsource_id         = Column(Integer, ForeignKey('dcsource.id'))
    DCsource            = relationship("DCSource", back_populates="phys_chans")

    log_chan            = relationship("LogicalChannel", backref="phys_chan",
                                foreign_keys = "[LogicalChannel.phys_chan_id]")

    transmitter_id      = Column(Integer, ForeignKey("transmitter.id"))
    transmitter         = relationship("Transmitter", back_populates="channels")

    receiver_id         = Column(Integer, ForeignKey("receiver.id"))
    receiver            = relationship("Receiver", back_populates="channels")

    def q(self):
        if isinstance(self.logical_channel, Qubit):
            return self.logical_channel

class LogicalChannel(ChannelMixin, Channel):
    '''
    The main class from which we will generate sequences.
    At some point it needs to be assigned to a physical channel.
        frequency: modulation frequency of the channel (can be positive or negative)
    '''
    frequency    = Column(Float, default=0.0, nullable=False)
    pulse_params = Column(MutableDict.as_mutable(PickleType), default={})

    phys_chan_id = Column(Integer, ForeignKey("physicalchannel.id"))
    gate_chan_id = Column(Integer, ForeignKey("logicalchannel.id"), nullable=True)
    gate_chan    = relationship("LogicalChannel", uselist = False,
                    foreign_keys=[gate_chan_id],
                    remote_side="LogicalChannel.id",
                    backref=backref("gated_chan", uselist=False))

class PhysicalMarkerChannel(PhysicalChannel, ChannelMixin):
    '''
    A digital output channel on an Transmitter.
        gate_buffer: How much extra time should be added onto the beginning of a gating pulse
        gate_min_width: The minimum marker pulse width
    '''
    id = Column(Integer, ForeignKey("physicalchannel.id"), primary_key=True)

    gate_buffer    = Column(Float, default=0.0, nullable=False)
    gate_min_width = Column(Float, default=0.0, nullable=False)
    sequence_file  = Column(String)
    channel        = Column(Integer, nullable=False)

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
    attenuation          = Column(Float, default=0.0, nullable=False)
    channel              = Column(Integer, nullable=False)
    sequence_file        = Column(String)

class AttenuatorChannel(PhysicalChannel, ChannelMixin):
    """
    Physical Channel on an Attenutator
    """
    id          = Column(Integer, ForeignKey("physicalchannel.id"), primary_key=True)
    channel     = Column(Integer, nullable=False)
    attenuation = Column(Float, default=0.0, nullable=False)

    attenuator_id = Column(Integer, ForeignKey("attenuator.id"))
    attenuator    = relationship("Attenuator", back_populates="channels")

class ReceiverChannel(PhysicalChannel, ChannelMixin):
    '''
    ReceiverChannel denotes the physical receive channel on a transceiver. The
    actual stream type, and the dsp stream id, are handled by the pipeline.
    '''
    id = Column(Integer, ForeignKey("physicalchannel.id"), primary_key=True)

    channel            = Column(Integer, nullable=False)
    triggering_chan    = relationship("Measurement", backref='receiver_chan', foreign_keys="[Measurement.receiver_chan_id]")
    attenuation        = Column(Integer)
    
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

    edge_source  = relationship("Edge", backref="source", foreign_keys="[Edge.source_id]")
    edge_target  = relationship("Edge", backref="target", foreign_keys="[Edge.target_id]")
    measure_chan = relationship("Measurement", uselist=False, backref="control_chan", foreign_keys="[Measurement.control_chan_id]")

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

    control_chan_id = Column(Integer, ForeignKey("qubit.id"))

    trig_chan       = relationship("LogicalMarkerChannel", uselist=False, backref="meas_chan", foreign_keys="[LogicalMarkerChannel.meas_chan_id]")
    receiver_chan_id = Column(Integer, ForeignKey("receiverchannel.id"))
    # attenuator_chan = relationship("AttenuatorChannel", uselist=False, backref="measuring_chan", foreign_keys="[AttenuatorChannel.measuring_chan_id]")

    @validates('meas_type')
    def validate_meas_type(self, key, source):
        assert source in ['autodyne', 'homodyne']
        return source

    def __init__(self, **kwargs):
        if "pulse_params" not in kwargs.keys():
            kwargs["pulse_params"] =  {'length': 100.0e-9,
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

    source_id = Column(Integer, ForeignKey("qubit.id"))
    target_id = Column(Integer, ForeignKey("qubit.id"))

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

    def isforward(self, source, target):
        ''' Test whether (source, target) matches the directionality of the edge. '''
        nodes = (self.source, self.target)
        if (source not in nodes) or (target not in nodes):
            raise ValueError('One of {0} is not a node in the edge'.format((
                source, target)))
        if (self.source, self.target) == (source, target):
            return True
        else:
            return False
