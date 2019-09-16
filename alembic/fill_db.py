from QGL import *
from auspex.qubit import *
import bbndb

cl = ChannelLibrary(db_resource_name="BBN.sqlite")
pl = PipelineManager()

# Create five qubits and supporting hardware
for i in range(5):
    q1 = cl.new_qubit(f"q{i}")
    cl.new_APS2(f"BBNAPS2-{2*i+1}", address=f"192.168.5.{101+2*i}") 
    cl.new_APS2(f"BBNAPS2-{2*i+2}", address=f"192.168.5.{102+2*i}")
    cl.new_X6(f"X6_{i}", address=0)
    cl.new_source(f"Holz{2*i+1}", "HolzworthHS9000", f"HS9004A-009-{2*i}", power=-30)
    cl.new_source(f"Holz{2*i+2}", "HolzworthHS9000", f"HS9004A-009-{2*i+1}", power=-30) 
    cl.set_control(cl[f"q{i}"], cl[f"BBNAPS2-{2*i+1}"], generator=cl[f"Holz{2*i+1}"])
    cl.set_measure(cl[f"q{i}"], cl[f"BBNAPS2-{2*i+2}"], cl[f"X6_{i}"][1], generator=cl[f"Holz{2*i+2}"])

cl.new_edge(cl["q1"], cl["q2"])
cl.new_edge(cl["q2"], cl["q3"])
cl.new_edge(cl["q3"], cl["q4"])
cl.save_as("cl_test")

pl.create_default_pipeline()
pl.save_as("test")
pl.save_as("another_test")

# Calibration DB
cl.session.add(bbndb.calibration.Sample(name="blub"))
cl.session.add(bbndb.calibration.Calibration(name="value", value=1.0))

cl.commit()