import numpy as np
from copy import deepcopy
import datetime
import networkx as nx

from sqlalchemy import Column, DateTime, String, Boolean, Float, Integer, LargeBinary, ForeignKey, func, JSON, PickleType
from sqlalchemy.orm import relationship, backref, validates
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy import inspect
from IPython.display import HTML, display

from . import session #session.Base, Session, engine

class Connection(session.Base):
    __tablename__ = "connection"
    id            = Column(Integer, primary_key=True)
    node1_id      = Column(Integer, ForeignKey("nodeproxy.id"))
    node2_id      = Column(Integer, ForeignKey("nodeproxy.id"))
    pipeline_name = Column(String, nullable=False)
    time          = Column(DateTime)

class NodeProxy(session.Base):
    __tablename__ = "nodeproxy"
    id              = Column(Integer, primary_key=True)
    label           = Column(String)
    qubit_name      = Column(String)
    node_type       = Column(String(50))
    connection_to   = relationship("Connection", backref='node1', foreign_keys="[Connection.node1_id]")
    connection_from = relationship("Connection", backref='node2', foreign_keys="[Connection.node2_id]")

    __mapper_args__ = {
        'polymorphic_identity':'channel',
        'polymorphic_on':node_type
    }

    def print(self):
        table_code = ""
        label = self.label if self.label else "Unlabeled"
        inspr = inspect(self)
        for c in list(self.__mapper__.columns):
            if c.name not in ["id", "label", "qubit_name", "node_type"]:
                hist = getattr(inspr.attrs, c.name).history
                dirty = "Yes" if hist.has_changes() else ""
                table_code += f"<tr><td>{c.name}</td><td>{getattr(self,c.name)}</td><td>{dirty}</td></tr>"
        display(HTML(f"<b>{self.node_type}</b> ({self.qubit_name}) <i>{label}</i></br><table><tr><th>Attribute</th><th>Value</th><th>Uncommitted Changes</th></tr><tr>{table_code}</tr></table>"))

class NodeMixin(object):
    @declared_attr
    def id(cls):
        return Column(Integer, ForeignKey("nodeproxy.id"), primary_key=True)
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

class FilterProxy(NodeMixin, NodeProxy):
    """docstring for FilterProxy"""

    def __init__(self, **kwargs):
        global __current_exp__
        # with db_session:
        super(FilterProxy, self).__init__(**kwargs)
        self.exp = __current_exp__

    def add(self, filter_obj):
        if not self.exp:
            raise Exception("This filter does not correspond to any experiment. Please file a bug report.")
        if not self.pipelineMgr:
            raise Exception("This filter does not know about any pipeline manager.")

        filter_obj.exp = self.exp
        filter_obj.pipelineMgr = self.pipelineMgr
        filter_obj.qubit_name = self.qubit_name

        self.exp.meas_graph.add_edge(self, filter_obj)
        self.pipelineMgr.session.add(filter_obj)
        return filter_obj

    def drop(self):
        desc = list(nx.algorithms.dag.descendants(self.exp.meas_graph, self))
        desc.append(self)
        self.exp.meas_graph.remove_nodes_from(desc)
        for n in desc:
            n.exp = None
            self.pipelineMgr.session.expunge(n)

    def node_label(self):
        label = self.label if self.label else ""
        return f"{self.__class__.__name__} {label} ({self.qubit_name})"

    def __repr__(self):
        return f"{self.__class__.__name__} {self.label} ({self.qubit_name})"

    def __str__(self):
        return f"{self.__class__.__name__} {self.label} ({self.qubit_name})"

    def __getitem__(self, key):
        ss = list(self.exp.meas_graph.successors(self))
        label_matches = [s for s in ss if s.label == key]
        class_matches = [s for s in ss if s.__class__.__name__ == key]
        if len(label_matches) == 1:
            return label_matches[0]
        elif len(class_matches) == 1:
            return class_matches[0]
        else:
            raise ValueError("Could not find suitable filter by label or by class")

class Demodulate(FilterProxy, NodeMixin):
    """Digital demodulation and filtering to select a signal at a particular frequency component. This
    filter does the following:

        1. First stage decimating filter on data
        2. Take product of result with with reference signal at demodulation frequency
        3. Second stage decimating filter on result to boost n_bandwidth
        4. Final channel selecting filter at n_bandwidth/2

    If an axis name is supplied to `follow_axis` then the filter will demodulate at the freqency
    `axis_frequency_value - follow_freq_offset` otherwise it will demodulate at `frequency`. Note that
    the filter coefficients are still calculated with respect to the `frequency` paramter, so it should
    be chosen accordingly when `follow_axis` is defined."""
    # Demodulation frequency
    id = Column(Integer, ForeignKey("filterproxy.id"), primary_key=True)

    frequency = Column(Float, default=10e6, nullable=False)
    @validates('frequency')
    def validate_frequency(self, key, value):
        assert (value >= -10.0e9) and (value <= 10.0e9)
        return value
    # Filter bandwidth
    bandwidth          = Column(Float, default=5e6, nullable=False)
    @validates('bandwidth')
    def validate_bandwidth(self, key, value):
        assert (value >= 0.0) and (value <= 100.0e6)
        return value
    # Let the demodulation frequency follow an axis' value (useful for sweeps)
    follow_axis        = Column(String) # Name of the axis to follow
    # Offset of the actual demodulation from the followed axis
    follow_freq_offset = Column(Float) # Offset
    # Maximum data reduction factor
    decimation_factor  = Column(Integer, default=4, nullable=False)
    @validates('decimation_factor')
    def validate_decimation_factor(self, key, value):
        assert value in range(1, 101)
        return value

class Average(FilterProxy, NodeMixin):
    """Takes data and collapses along the specified axis."""
    # Over which axis should averaging take place
    id = Column(Integer, ForeignKey("filterproxy.id"), primary_key=True)

    axis = Column(String, default="averages")

class Integrate(FilterProxy, NodeMixin):
    id = Column(Integer, ForeignKey("filterproxy.id"), primary_key=True)
    """Integrate with a given kernel or using a simple boxcar.
    Kernel will be padded/truncated to match record length"""
    # Use a boxcar (simple) or use a kernel specified by the kernel_filename parameter
    simple_kernel   = Column(Boolean, default=True, nullable=False)
    # File in which to find the kernel data, or raw python string to be evaluated
    kernel          = Column(String)
    # DC bias
    bias            = Column(Float, default=0.0, nullable=False)
    # For a simple kernel, where does the boxcar start
    box_car_start   = Column(Float, default=0.0, nullable=False)
    @validates('box_car_start')
    def validate_box_car_start(self, key, value):
        assert (value >= 0.0) and (value <= 1e-4)
        return value
    # For a simple kernel, where does the boxcar stop
    box_car_stop    = Column(Float, default=100.0e-9, nullable=False)
    @validates('box_car_stop')
    def validate_box_car_stop(self, key, value):
        assert (value >= 0.0) and (value <= 1e-4)
        return value
    # Built in frequency for demodulation
    demod_frequency = Column(Float, default=0.0, nullable=False)

class OutputProxy(FilterProxy, NodeMixin):
    id = Column(Integer, ForeignKey("filterproxy.id"), primary_key=True)

class Display(OutputProxy, NodeMixin):
    """Create a plot tab within the plotting interface."""
    # Should we plot in 1D or 2D? 0 means choose the largest possible.
    id = Column(Integer, ForeignKey("outputproxy.id"), primary_key=True)
    plot_dims = Column(Integer, default=0, nullable=False)
    @validates('plot_dims')
    def validate_plot_dims(self, key, value):
        assert value in [0,1,2]
        return value
    # Allowed values are "real", "imag", "real/imag", "amp/phase", "quad"
    # TODO: figure out how to validate these in pony
    plot_mode = Column(String, default="quad", nullable=False)

class Write(OutputProxy, NodeMixin):
    """Writes data to file."""
    id = Column(Integer, ForeignKey("outputproxy.id"), primary_key=True)
    filename      = Column(String,  default = "auspex_default.h5", nullable=False)
    groupname     = Column(String,  default = "main", nullable=False)
    add_date      = Column(Boolean, default = False, nullable=False)
    save_settings = Column(Boolean, default = True, nullable=False)

class Buffer(OutputProxy, NodeMixin):
    """Saves data in a buffer"""
    id = Column(Integer, ForeignKey("outputproxy.id"), primary_key=True)
    max_size = Column(Integer)

class QubitProxy(NodeMixin, NodeProxy):
    """docstring for FilterProxy"""
    id = Column(Integer, ForeignKey("nodeproxy.id"), primary_key=True)

    def __init__(self, exp, qubit_name):
        global __current_exp__
        super(QubitProxy, self).__init__(qubit_name=qubit_name)
        self.exp = exp
        __current_exp__ = exp
        # self.qubit_name = qubit_name
        self.digitizer_settings = None
        self.available_streams = None
        self.stream_type = None

    def add(self, filter_obj):
        if not self.exp:
            raise Exception("This qubit does not correspond to any experiment. Please file a bug report.")
        if not self.pipelineMgr:
            raise Exception("This qubit does not know about any pipeline manager.")

        filter_obj.qubit_name  = self.qubit_name
        filter_obj.pipelineMgr = self.pipelineMgr
        filter_obj.exp         = self.exp
        self.exp.meas_graph.add_edge(self, filter_obj)
        self.pipelineMgr.session.add(filter_obj)

        return filter_obj

    def set_stream_type(self, stream_type):
        if stream_type not in ["raw", "demodulated", "integrated", "averaged"]:
            raise ValueError(f"Stream type {stream_type} must be one of raw, demodulated, integrated, or result.")
        if stream_type not in self.available_streams:
            raise ValueError(f"Stream type {stream_type} is not avaible for {self.qubit_name}. Must be one of {self.available_streams}")
        self.stream_type = stream_type

    def clear_pipeline(self):
        """Remove all nodes coresponding to the qubit"""
        desc = nx.algorithms.dag.descendants(self.exp.meas_graph, self)
        for n in desc:
            n.exp = None
            self.pipelineMgr.session.expunge(n)
        self.exp.meas_graph.remove_nodes_from(desc)
        
    def create_default_pipeline(self, buffers=False):
        Output = Buffer if buffers else Write
        if self.stream_type.lower() == "raw":
            self.add(Demodulate()).add(Integrate()).add(Average()).add(Output())
        if self.stream_type.lower() == "demodulated":
            self.add(Integrate()).add(Average()).add(Output())
        if self.stream_type.lower() == "integrated":
            self.add(Average()).add(Output())
        if self.stream_type.lower() == "averaged":
            self.add(Output())

    def show_pipeline(self):
        desc = list(nx.algorithms.dag.descendants(self.exp.meas_graph, self)) + [self]
        labels = {n: n.node_label() for n in desc}
        subgraph = self.exp.meas_graph.subgraph(desc)
        colors = ["#3182bd" if isinstance(n, QubitProxy) else "#ff9933" for n in subgraph.nodes()]
        self.exp.plot_graph(subgraph, labels, colors=colors, prog='dot')

    def show_connectivity(self):
        pass

    def node_label(self):
        return self.__repr__()

    def __repr__(self):
        return f"Qubit {self.qubit_name}"

    def __str__(self):
        return f"Qubit {self.qubit_name}"

    def __getitem__(self, key):
        ss = list(self.exp.meas_graph.successors(self))
        label_matches = [s for s in ss if s.label == key]
        class_matches = [s for s in ss if s.__class__.__name__ == key]
        if len(label_matches) == 1:
            return label_matches[0]
        elif len(class_matches) == 1:
            return class_matches[0]
        else:
            raise ValueError("Could not find suitable filter by label or by class")

stream_hierarchy = [Demodulate, Integrate, Average, OutputProxy]
