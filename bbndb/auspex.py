import numpy as np
from copy import deepcopy
import datetime
import networkx as nx

from sqlalchemy import Column, DateTime, String, Boolean, Float, Integer, LargeBinary, ForeignKey, func, JSON, PickleType
from sqlalchemy.orm import relationship, backref, validates
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy import inspect
from IPython.display import HTML, display
from .session import Base

__current_pipeline__ = None

class Connection(Base):
    __tablename__ = "connection"
    id            = Column(Integer, primary_key=True)
    node1_id      = Column(Integer, ForeignKey("nodeproxy.id"))
    node2_id      = Column(Integer, ForeignKey("nodeproxy.id"))
    node1_name    = Column(String, nullable=False, default="source")
    node2_name    = Column(String, nullable=False, default="sink")
    pipeline_name = Column(String, nullable=False)
    time          = Column(DateTime)

class NodeProxy(Base):
    __tablename__ = "nodeproxy"
    id              = Column(Integer, primary_key=True)
    label           = Column(String)
    qubit_name      = Column(String)
    node_type       = Column(String(50))
    hash_val        = Column(Integer, nullable=False)
    connection_to   = relationship("Connection", uselist=False, backref='node1', foreign_keys="[Connection.node1_id]")
    connection_from = relationship("Connection", uselist=False, backref='node2', foreign_keys="[Connection.node2_id]")

    __mapper_args__ = {
        'polymorphic_identity':'channel',
        'polymorphic_on':node_type
    }

    def __init__(self, **kwargs):
        self.hash_val = int(np.random.randint(np.iinfo(np.uint32).max, dtype=np.uint32))
        super().__init__(**kwargs)

    def print(self, show=True):
        table_code = ""
        label = self.label if self.label else "Unlabeled"
        inspr = inspect(self)
        for c in list(self.__mapper__.columns):
            if c.name not in ["id", "label", "qubit_name", "node_type"]:
                hist = getattr(inspr.attrs, c.name).history
                dirty = "Yes" if hist.has_changes() else ""
                if c.name == "kernel_data":
                    table_code += f"<tr><td>{c.name}</td><td>Binary Data of length {len(self.kernel)}</td><td>{dirty}</td></tr>"
                else:
                    table_code += f"<tr><td>{c.name}</td><td>{getattr(self,c.name)}</td><td>{dirty}</td></tr>"
        html = f"<b>{self.node_type}</b> ({self.qubit_name}) <i>{label}</i></br><table style='{{padding:0.5em;}}'><tr><th>Attribute</th><th>Value</th><th>Changes?</th></tr><tr>{table_code}</tr></table>"
        if show:
            display(HTML(html))
        else:
            return html

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
        global __current_pipeline__
        # with db_session:
        super(FilterProxy, self).__init__(**kwargs)
        self.pipelineMgr = __current_pipeline__

    def add(self, filter_obj, connector_out="source", connector_in="sink"):
        # if not self.pipeline:
        #     raise Exception("This filter does not correspond to any experiment. Please file a bug report.")
        if not self.pipelineMgr:
            raise Exception("This filter does not know about any pipeline manager.")

        filter_obj.pipelineMgr = self.pipelineMgr
        filter_obj.qubit_name = self.qubit_name
        self.pipelineMgr.meas_graph.add_node(filter_obj.hash_val, node_obj=filter_obj)
        self.pipelineMgr.meas_graph.add_edge(self.hash_val, filter_obj.hash_val, connector_in=connector_in, connector_out=connector_out)
        self.pipelineMgr.session.add(filter_obj)
        return filter_obj

    def drop(self):
        desc_hashes = list(nx.algorithms.dag.descendants(self.pipelineMgr.meas_graph, self.hash_val))
        desc_hashes.append(self.hash_val)
        desc_objs = []
        for n in desc_hashes:
            # n.exp = None
            n = self.pipelineMgr.meas_graph.nodes[n]['node_obj']
            desc_objs.append(n)
            self.pipelineMgr.session.expunge(n)
        self.pipelineMgr.meas_graph.remove_nodes_from(desc_objs+[self])

    def node_label(self):
        label = self.label if self.label else ""
        return f"{self.__class__.__name__} {label} ({self.qubit_name})"

    def __repr__(self):
        return f"{self.__class__.__name__} {self.label} ({self.qubit_name})"

    def __str__(self):
        return f"{self.__class__.__name__} {self.label} ({self.qubit_name})"

    def __getitem__(self, key):
        ss = list(self.pipelineMgr.meas_graph.successors(self.hash_val))
        label_matches = [self.pipelineMgr.meas_graph.nodes[s]['node_obj'] for s in ss if self.pipelineMgr.meas_graph.nodes[s]['node_obj'].label == key]
        class_matches = [self.pipelineMgr.meas_graph.nodes[s]['node_obj'] for s in ss if self.pipelineMgr.meas_graph.nodes[s]['node_obj'].__class__.__name__ == key]
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
    """Takes data and collapses along the specified axis. Threshold is used for
    state identification."""
    id = Column(Integer, ForeignKey("filterproxy.id"), primary_key=True)
    axis = Column(String, default="averages")
    threshold = Column(Float, default=0.5)

class Framer(FilterProxy, NodeMixin):
    """Emit out data in increments defined by the specified axis."""
    id = Column(Integer, ForeignKey("filterproxy.id"), primary_key=True)
    axis = Column(String, nullable=False)

class FidelityKernel(FilterProxy, NodeMixin):
    """Calculates the single shot fidelity from given input"""
    id                       = Column(Integer, ForeignKey("filterproxy.id"), primary_key=True)
    save_kernel              = Column(Boolean, nullable=False, default=False)
    optimal_integration_time = Column(Boolean, nullable=False, default=False)
    set_threshold            = Column(Boolean, nullable=False, default=True)
    zero_mean                = Column(Boolean, nullable=False, default=False)
    logistic_regression      = Column(Boolean, nullable=False, default=False)
    tolerance                = Column(Float, nullable=False, default=1.0e-3)

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
    filename      = Column(String,  default = "output.auspex", nullable=False)
    groupname     = Column(String,  default = "main", nullable=False)
    add_date      = Column(Boolean, default = False, nullable=False)
    # save_settings = Column(Boolean, default = True, nullable=False)

class Buffer(OutputProxy, NodeMixin):
    """Saves data in a buffer"""
    id = Column(Integer, ForeignKey("outputproxy.id"), primary_key=True)
    max_size = Column(Integer)

    def __init__(self, **kwargs):
        if "groupname" in kwargs:
            kwargs.pop("groupname")
        super(Buffer, self).__init__(**kwargs)

class StreamSelect(NodeMixin, NodeProxy):
    """docstring for FilterProxy"""
    id = Column(Integer, ForeignKey("nodeproxy.id"), primary_key=True)

    dsp_channel = Column(Integer, default=0, nullable=False)
    stream_type = Column(String, default='raw', nullable=False)
    @validates('stream_type')
    def validate_stream_type(self, key, value):
        assert (value in ["raw", "demodulated", "integrated", "averaged"])
        return value

    dsp_channel        = Column(Integer, default=1)
    if_freq            = Column(Float, default=0.0, nullable=False)
    kernel_data        = Column(LargeBinary) # Binary string of np.complex128
    kernel_bias        = Column(Float, default=0.0, nullable=False)
    threshold          = Column(Float, default=0.0, nullable=False)
    threshold_invert   = Column(Boolean, default=False, nullable=False)

    def kernel():
        doc = "The kernel as represented by a numpy complex128 array"
        def fget(self):
            if self.kernel_data:
                return np.frombuffer(self.kernel_data, dtype=np.complex128)
            else:
                return np.empty((0,), dtype=np.complex128)
        def fset(self, value):
            self.kernel_data = value.astype(np.complex128).tobytes()
        return locals()
    kernel = property(**kernel())

    def __init__(self, pipelineMgr=None, **kwargs):
        global __current_pipeline__
        super(StreamSelect, self).__init__(**kwargs)
        self.pipelineMgr = pipelineMgr
        __current_pipeline__ = pipelineMgr
        self.digitizer_settings = None
        self.available_streams = None

    def add(self, filter_obj, connector_out="source", connector_in="sink"):
        # if not self.pipeline:
        #     raise Exception("This qubit does not correspond to any experiment. Please file a bug report.")
        if not self.pipelineMgr:
            raise Exception("This qubit does not know about any pipeline manager.")

        filter_obj.qubit_name  = self.qubit_name
        filter_obj.pipelineMgr = self.pipelineMgr
        # filter_obj.exp         = self.pipeline
        if self.hash_val not in self.pipelineMgr.meas_graph.nodes():
            self.pipelineMgr.meas_graph.add_node(self.hash_val, node_obj=self)
        self.pipelineMgr.meas_graph.add_node(filter_obj.hash_val, node_obj=filter_obj)
        self.pipelineMgr.meas_graph.add_edge(self.hash_val, filter_obj.hash_val, connector_in=connector_in, connector_out=connector_out)
        self.pipelineMgr.session.add(filter_obj)

        return filter_obj

    def clear_pipeline(self):
        """Remove all nodes coresponding to the qubit"""
        desc = nx.algorithms.dag.descendants(self.pipelineMgr.meas_graph, self.hash_val)
        for n in desc:
            # n.exp = None
            n = self.pipelineMgr.meas_graph.nodes[n]['node_obj']
            self.pipelineMgr.session.expunge(n)
        self.pipelineMgr.meas_graph.remove_nodes_from(desc)

    def create_default_pipeline(self, average=True, buffers=False):
        Output = Buffer if buffers else Write
        if average:
            if self.stream_type.lower() == "raw":
                self.add(Demodulate()).add(Integrate()).add(Average()).add(Output(groupname=self.qubit_name+'-main'))
            if self.stream_type.lower() == "demodulated":
                self.add(Integrate()).add(Average()).add(Output(groupname=self.qubit_name+'-main'))
            if self.stream_type.lower() == "integrated":
                self.add(Average()).add(Output(groupname=self.qubit_name+'-main'))
            if self.stream_type.lower() == "averaged":
                self.add(Output(groupname=self.qubit_name+'-main'))
        else:
            if self.stream_type.lower() == "raw":
                self.add(Demodulate()).add(Integrate()).add(Output(groupname=self.qubit_name+'-main'))
            if self.stream_type.lower() == "demodulated":
                self.add(Integrate()).add(Output(groupname=self.qubit_name+'-main'))
            if self.stream_type.lower() == "integrated":
                self.add(Output(groupname=self.qubit_name+'-main'))
            if self.stream_type.lower() == "averaged":
                raise Exception("Cannot have averaged stream without averaging?!")

    def show_pipeline(self):
        desc = list(nx.algorithms.dag.descendants(self.pipelineMgr.meas_graph, self.hash_val)) + [self.hash_val]
        subgraph = self.pipelineMgr.meas_graph.subgraph(desc)
        return self.pipelineMgr.show_pipeline(subgraph=subgraph)

    def show_connectivity(self):
        pass

    def node_label(self):
        return self.__repr__()

    def __repr__(self):
        return f"StreamSelect for {self.qubit_name}"

    def __str__(self):
        return f"StreamSelect for {self.qubit_name}"

    def __getitem__(self, key):
        ss = list(self.pipelineMgr.meas_graph.successors(self.hash_val))
        label_matches = [self.pipelineMgr.meas_graph.nodes[s]['node_obj'] for s in ss if self.pipelineMgr.meas_graph.nodes[s]['node_obj'].label == key]
        class_matches = [self.pipelineMgr.meas_graph.nodes[s]['node_obj'] for s in ss if self.pipelineMgr.meas_graph.nodes[s]['node_obj'].__class__.__name__ == key]
        if len(label_matches) == 1:
            return label_matches[0]
        elif len(class_matches) == 1:
            return class_matches[0]
        else:
            raise ValueError("Could not find suitable filter by label or by class")

stream_hierarchy = [Demodulate, Integrate, Average, OutputProxy]
