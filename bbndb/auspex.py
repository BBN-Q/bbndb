from pony.orm import *
import networkx as nx
from functools import wraps

# Get these in global scope for module imports
Connection       = None
NodeProxy        = None
FilterProxy      = None
Demodulate       = None
Average          = None
Integrate        = None
OutputProxy      = None
Display          = None
Write            = None
Buffer           = None
QubitProxy       = None
stream_hierarchy = None

__current_exp__ = None

def define_entities(db):

    def localize_db_objects(f):
        """Since we can't mix db objects from separate sessions, re-fetch entities by their unique IDs"""
        @wraps(f)
        def wrapper(*args, **kwargs):
            with db_session:
                args_info    = [(type(arg), arg.id) if isinstance(arg, db.Entity) else (arg, None) for arg in args]
                kwargs_info  = {k: (type(v), v.id) if isinstance(v, db.Entity) else (v, None) for k, v in kwargs.items()}
            with db_session:
                new_args   = [c[i] if i else c for c, i in args_info]
                new_kwargs = {k: v[0][v[1]] if v[1] else v[0] for k,v in kwargs_info.items()}
                return f(*new_args, **new_kwargs)
        return wrapper

    class Connection(db.Entity):
        node1         = Required("NodeProxy")
        node2         = Required("NodeProxy")
        pipeline_name = Required(str)

    class NodeProxy(db.Entity):
        label           = Optional(str)
        qubit_name      = Optional(str)
        connection_to   = Set(Connection, reverse='node1')
        connection_from = Set(Connection, reverse='node2')

    class FilterProxy(NodeProxy):
        """docstring for FilterProxy"""

        def __init__(self, **kwargs):
            global __current_exp__
            with db_session:
                super(FilterProxy, self).__init__(**kwargs)
            self.exp = __current_exp__

        def add(self, filter_obj):
            if not self.exp:
                print("This filter may have been orphaned by a clear_pipeline call!")
                return

            commit() # Make sure filter_obj is in the db
            
            filter_obj.exp = self.exp
            with db_session:
                FilterProxy[filter_obj.id].qubit_name = self.qubit_name
                commit()
                fp = FilterProxy[filter_obj.id]
            self.exp.meas_graph.add_edge(self, fp)
            return fp

        def node_label(self):
            return f"{self.__class__.__name__} {self.label}\n({self.qubit_name})"

        def __repr__(self):
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

    class Demodulate(FilterProxy):
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
        frequency          = Required(float, default=10e6, min=-10e9, max=10e9)
        # Filter bandwidth
        bandwidth          = Required(float, default=5e6, min=0.0, max=100e6)
        # Let the demodulation frequency follow an axis' value (useful for sweeps)
        follow_axis        = Optional(str) # Name of the axis to follow
        # Offset of the actual demodulation from the followed axis
        follow_freq_offset = Optional(float) # Offset
        # Maximum data reduction factor
        decimation_factor  = Required(int, default=4, min=1, max=100)

    class Average(FilterProxy):
        """Takes data and collapses along the specified axis."""
        # Over which axis should averaging take place
        axis = Optional(str, default="averages")

    class Integrate(FilterProxy):
        """Integrate with a given kernel or using a simple boxcar.
        Kernel will be padded/truncated to match record length"""
        # Use a boxcar (simple) or use a kernel specified by the kernel_filename parameter
        simple_kernel   = Required(bool, default=True)
        # File in which to find the kernel data, or raw python string to be evaluated
        kernel          = Optional(str)
        # DC bias
        bias            = Required(float, default=0.0)
        # For a simple kernel, where does the boxcar start
        box_car_start   = Required(float, default=0.0, min=0.0)
        # For a simple kernel, where does the boxcar stop
        box_car_stop    = Required(float, default=100.0e-9, min=0.0)
        # Built in frequency for demodulation
        demod_frequency = Required(float, default=0.0)

    class OutputProxy(FilterProxy):
        pass

    class Display(OutputProxy):
        """Create a plot tab within the plotting interface."""
        # Should we plot in 1D or 2D? 0 means choose the largest possible.
        plot_dims = Required(int, default=0, min=0, max=2)
        # Allowed values are "real", "imag", "real/imag", "amp/phase", "quad"
        # TODO: figure out how to validate these in pony
        plot_mode = Required(str, default="quad")

    class Write(OutputProxy):
        """Writes data to file."""
        filename      = Required(str,  default = "auspex_default.h5")
        groupname     = Required(str,  default = "main")
        add_date      = Required(bool, default = False)
        save_settings = Required(bool, default = True)

    class Buffer(OutputProxy):
        """Saves data in a buffer"""
        max_size = Optional(int)

    class QubitProxy(NodeProxy):
        """docstring for FilterProxy"""

        def __init__(self, exp, qubit_name):
            global __current_exp__
            super(QubitProxy, self).__init__(qubit_name=qubit_name)
            self.exp = exp
            __current_exp__ = exp
            # self.qubit_name = qubit_name
            self.digitizer_settings = None
            self.available_streams = None
            self.stream_type = None

        # @localize_db_objects
        def add(self, filter_obj):
            if not self.exp:
                print("This qubit may have been orphaned!")
                return

            commit() # Make sure filter_obj is in the db
            
            
            with db_session:
                FilterProxy[filter_obj.id].qubit_name = self.qubit_name
                FilterProxy[filter_obj.id].exp = self.exp
                commit()
                fp = FilterProxy[filter_obj.id]
            self.exp.meas_graph.add_edge(self, fp)

            return fp

        def set_stream_type(self, stream_type):
            if stream_type not in ["raw", "demodulated", "integrated", "averaged"]:
                raise ValueError(f"Stream type {stream_type} must be one of raw, demodulated, integrated, or result.")
            if stream_type not in self.available_streams:
                raise ValueError(f"Stream type {stream_type} is not avaible for {self.qubit_name}. Must be one of {self.available_streams}")
            self.stream_type = stream_type

        def clear_pipeline(self):
            """Remove all nodes coresponding to the qubit"""
            # nodes_to_remove = [n for n in self.exp.meas_graph.nodes() if n.qubit_name == self.qubit_name]
            # self.exp.meas_graph.remove_nodes_from(nodes_to_remove)
            desc = nx.algorithms.dag.descendants(self.exp.meas_graph, self)
            for n in desc:
                n.exp = None
            self.exp.meas_graph.remove_nodes_from(desc)

        def auto_create_pipeline(self, buffers=False):
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

    globals()["Connection"] = Connection
    globals()["NodeProxy"] = NodeProxy
    globals()["FilterProxy"] = FilterProxy
    globals()["Demodulate"] = Demodulate
    globals()["Average"] = Average
    globals()["Integrate"] = Integrate
    globals()["OutputProxy"] = OutputProxy
    globals()["Display"] = Display
    globals()["Write"] = Write
    globals()["Buffer"] = Buffer
    globals()["QubitProxy"] = QubitProxy
    globals()["stream_hierarchy"] = [Demodulate, Integrate, Average, OutputProxy]
