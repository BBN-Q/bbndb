import numpy as np
from math import tan, cos, pi
from copy import deepcopy
import datetime

from sqlalchemy import Column, DateTime, String, Boolean, Float, Integer, LargeBinary, ForeignKey, func, JSON, PickleType
from sqlalchemy.orm import relationship, backref, validates
from sqlalchemy.ext.declarative import declarative_base, declared_attr

Base = declarative_base()

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
    id           = Column(Integer, primary_key=True)
    label        = Column(String, nullable=False)
    channels     = relationship("Channel", backref="channel_db", cascade="all, delete, delete-orphan")
    sources      = relationship("Source", backref="channel_db", cascade="all, delete, delete-orphan")
    transmitters = relationship("Transmitter", backref="channel_db", cascade="all, delete, delete-orphan")
    receivers    = relationship("Receiver", backref="channel_db", cascade="all, delete, delete-orphan")
    transceivers = relationship("Transceiver", backref="channel_db", cascade="all, delete, delete-orphan")
    instruments  = relationship("Instrument", backref="channel_db", cascade="all, delete, delete-orphan")
    processors   = relationship("Processor", backref="channel_db", cascade="all, delete, delete-orphan")
    time         = Column(DateTime)
    def __repr__(self):
        return str(self)
    def __str__(self):
        return f"ChannelDatabase(id={self.id}, label={self.label})"

class Instrument(DatabaseItem, Base):
    model      = Column(String, nullable=False)
    address    = Column(String)
    parameters = Column(PickleType, default={}, nullable=False)
    
class Source(DatabaseItem, Base):
    model           = Column(String, nullable=False)
    address         = Column(String)
    power           = Column(Float, nullable=False)
    frequency       = Column(Float, nullable=False)
    # logicalchannel  = relationship("LogicalChannel", back_populates="generator")
    # physicalchannel_id = Column(Integer, ForeignKey("physicalchannel.id"))
    # relationship("PhysicalChannel", back_populates="generator")
    
class Receiver(DatabaseItem, Base):
    """A receiver , or generally an analog to digitial converter"""
    model            = Column(String, nullable=False)
    address          = Column(String)
    stream_types     = Column(String, default="raw", nullable=False)
#     channels         = relationship("ReceiverChannel")
    trigger_source   = Column(String, default="External", nullable=False)
    record_length    = Column(Integer, default=1024, nullable=False)
    sampling_rate    = Column(Float, default=1e9, nullable=False)
    number_segments  = Column(Integer, default=1) # This should be automati, nullable=Falsec
    number_waveforms = Column(Integer, default=1) # This should be automati, nullable=Falsec
    number_averages  = Column(Integer, default=100) # This should be automati, nullable=Falsec
    transceiver_id   = Column(Integer, ForeignKey("transceiver.id"))
    # acquire_mode     = Column(String,default="receiver ", py_check=lambda x: x in ['receiver ', 'averager'], nullable=False)

    @validates('trigger_source')
    def validate_trigger_source(self, key, source):
        assert source in ['External', 'Internal']
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
    # channels         = relationship("PhysicalChannel", back_populates="transmitter")
    trigger_interval = Column(Float, default=100e-6, nullable=False)
    trigger_source   = Column(String, default="External", nullable=False)
    delay            = Column(Float, default=0.0, nullable=False)
    master           = Column(Boolean, default=False, nullable=False)
    sequence_file    = Column(String)
    transceiver_id   = Column(Integer, ForeignKey("transceiver.id"))

    @validates('trigger_source')
    def validate_trigger_source(self, key, source):
        assert source in ['External', 'Internal']
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
    receivers    = relationship("Receiver", backref="transceiver")
    transmitters = relationship("Transmitter", backref="transceiver")
    processors   = relationship("Processor", backref="transceiver")
    master       = Column(String)

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
    generator_id    = Column(Integer, ForeignKey("source.id"))
    # generator       = relationship(Source, back_populates="physicalchannel")
    sampling_rate   = Column(Float, default=1.2e9, nullable=False)
    delay           = Column(Float, default=0.0, nullable=False)

# #     # Column reverse connection, nullable=Falses
#     # logicalchannel_id = Column(Integer, ForeignKey("channel.id"))
#     # logicalchannel    = relationship("LogicalChannel", backref=backref('physicalchannel', remote_side=[Channel.id]))
#     # transmitter_id  = Column(Integer, ForeignKey("transmitter.id"))
#     # transmitter     = relationship("Transmitter", back_populates="channels")

#     # def q(self):
#         # if isinstance(self.logical_channel, Qubit):
#             # return self.logical_channel

# class LogicalChannel(ChannelMixin, Channel):
#     '''
#     The main class from which we will generate sequences.
#     At some point it needs to be assigned to a physical channel.
#         frequency: modulation frequency of the channel (can be positive or negative)
#     '''
#     #During initilization we may just have a string reference to the channel
#     # physicalchannel_id = Column(Integer, ForeignKey("channel.id"))
#     frequency          = Column(Float, default=0.0, nullable=False)
#     pulse_params       = Column(PickleType, default={})
#     # gate_chan_id       = Column(Integer, ForeignKey("logicalmarkerchannel.id"))
#     # gate_chan          = relationship("LogicalMarkerChannel", backref="meas_channel")
#     # receiver_chan_id   = Column(Integer, ForeignKey("receiverchannel.id"))
#     # receiver_chan      = relationship("ReceiverChannel", back_populates="triggering_chan")


# class PhysicalMarkerChannel(PhysicalChannel):
#     '''
#     A digital output channel on an Transmitter.
#         gate_buffer: How much extra time should be added onto the beginning of a gating pulse
#         gate_min_width: The minimum marker pulse width
#     '''
#     gate_buffer    = Column(Float, default=0.0, nullable=False)
#     gate_min_width = Column(Float, default=0.0, nullable=False)
#     # phys_channel   = relationship("PhysicalChannel")

# class PhysicalQuadratureChannel(PhysicalChannel):
#     '''
#     Something used to implement a standard qubit channel with two analog channels and a microwave gating channel.
#     '''
#     amp_factor           = Column(Float, default=1.0, nullable=False)
#     phase_skew           = Column(Float, default=0.0, nullable=False)
#     I_channel_offset     = Column(Float, default=0.0, nullable=False)
#     Q_channel_offset     = Column(Float, default=0.0, nullable=False)
#     I_channel_amp_factor = Column(Float, default=1.0, nullable=False)
#     Q_channel_amp_factor = Column(Float, default=1.0, nullable=False)

# class ReceiverChannel(PhysicalChannel):
#     '''
#     A trigger input on a receiver.
#     '''
#     triggering_channel = Column(LogicalChannel)
#     channel            = Column(Integer, nullable=False)
#     dsp_channel        = Column(Integer)
#     stream_type        = Column(String, default="raw", nullable=False) #, py_check=lambda x: x in["raw", "demodulated", "integrated", "averaged"],
#     if_freq            = Column(Float, default=0.0, nullable=False)
#     kernel             = Column(LargeBinary) # Float64 byte representation of kernel
#     kernel_bias        = Column(Float, default=0.0, nullable=False)
#     threshold          = Column(Float, default=0.0, nullable=False)
#     threshold_invert   = Column(Boolean, default=False, nullable=False)
#     receiver           = Column(Receiver)

# # def pulse_check(name):
# #     return name in ["constant", "gaussian", "drag", "gaussOn", "gaussOff", "dragGaussOn", "dragGaussOff",
# #                    "tanh", "exp_decay", "autodyne", "arb_axis_drag"]

# class LogicalMarkerChannel(LogicalChannel):
#     '''
#     A class for digital channels for gating sources or triggering other things.
#     '''
#     meas_channel    = Column(LogicalChannel)
#     trig_channel_id = Column(Integer, ForeignKey("measurement.id"))
#     trig_channel    = relationship("Measurement", back_populates="marker_chan")

#     # def __init__(self, **kwargs):
#     #     if "pulse_params" not in kwargs.keys():
#     #         kwargs["pulse_params"] =  {'shape_fun': "constant",'length': 10e-9}
#     #     super(LogicalMarkerChannel, self).__init__(**kwargs)

# class Qubit(LogicalChannel):
#     '''
#     The main class for generating qubit pulses.  Effectively a logical "QuadratureChannel".
#         frequency: modulation frequency of the channel (can be positive or negative)
#     '''
#     edge_source_id = Column(Integer, ForeignKey("edge.id"))
#     edge_source    = relationship("Edge", back_populates="source")
#     edge_target_id = Column(Integer, ForeignKey("edge.id"))
#     edge_target    = relationship("Edge", back_populates="target")

#     # def __init__(self, **kwargs):
#     #     if "pulse_params" not in kwargs.keys():
#     #         kwargs["pulse_params"] =  {'length': 20e-9,
#     #                         'piAmp': 1.0,
#     #                         'pi2Amp': 0.5,
#     #                         'shape_fun': "gaussian",
#     #                         'cutoff': 2,
#     #                         'drag_scaling': 0,
#     #                         'sigma': 5e-9}
#     #     super(Qubit, self).__init__(**kwargs)

# class Measurement(LogicalChannel):
#     '''
#     A class for measurement channels.
#     Measurements are special because they can be different types:
#     autodyne which needs an IQ pair or hetero/homodyne which needs just a marker channel.
#         meas_type: Type of measurement (autodyne, homodyne)
#         autodyne_freq: use to bake the modulation into the pulse, so that it has constant phase
#         frequency: use to asssociate modulation with the channel
#     '''
#     meas_type     = Column(String, default='autodyne', py_check=lambda x: x in ['autodyne', 'homodyne'], nullable=False)
#     autodyne_freq = Column(Float, default=0.0, nullable=False)
#     trig_chan     = Column(LogicalMarkerChannel)

#     # def __init__(self, **kwargs):
#     #     if "pulse_params" not in kwargs.keys():
#     #         kwargs["pulse_params"] =  {'length': 100e-9,
#     #                             'amp': 1.0,
#     #                             'shape_fun': "tanh",
#     #                             'cutoff': 2,
#     #                             'sigma': 1e-9}
#     #     super(Measurement, self).__init__(**kwargs)

# class Edge(LogicalChannel):
#     '''
#     Defines an arc/directed edge between qubit vertices. If a device supports bi-directional
#     connectivity, that is represented with two independent Edges.

#     An Edge is also effectively an abstract channel, so it carries the same properties as a
#     Qubit channel.
#     '''
#     # allow string in source and target so that we can store a label or an object
#     source = Column(Qubit, nullable=False)
#     target = Column(Qubit, nullable=False)

#     # def __init__(self, **kwargs):
#     #     if "pulse_params" not in kwargs.keys():
#     #         kwargs["pulse_params"] =   {'length': 20e-9,
#     #                                     'amp': 1.0,
#     #                                     'phase': 0.0,
#     #                                     'shape_fun': "gaussian",
#     #                                     'cutoff': 2,
#     #                                     'drag_scaling': 0,
#     #                                     'sigma': 5e-9,
#     #                                     'riseFall': 20e-9}
#     #     super(Edge, self).__init__(**kwargs)

if __name__ == '__main__':
    
    from sqlalchemy import create_engine
    engine = create_engine('sqlite:///:memory:', echo=True)
    Base.metadata.create_all(engine)

    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(bind=engine)
    session = Session()

    b = ChannelDatabase(label="working2")
    s = Source(label="Src1", model="abc", power=10.0, frequency=5.0e9)
    b.sources.append(s)
    session.add_all([b,s])
    session.new
    session.commit()





