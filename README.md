# BBNDB

**bbndb** is a configuration database for the BBN Qubit Measurement Framework. Used by both Auspex and QGL as a shared, versioned, means of storing instrument, qubit, and filter configurations. It is based on SQLAlchemy framework.

**QGL** is the Quantum Gate Language embedded in the python programming language. QGL is used to programmatically express sophisticated quantum gate sequences and its programming constructs look very similar to python programming constructs. QGL relies on the concept of a "channel" which embodies the physical realization of a qubit in an experimental configuration or a simulation configuration. **bbndb** is one way to manage, specify and store these configurations comprising information such as physical qubit attributes, simulation or equipment mappings, and physical couplings between qubits. 

**Auspex** is an experiment control framework which greatly facilitates executing QGL programs on laboratory hardware. Auspex provides constructs for abstracting (defining) instruments, connectivity, and post processing to enable "hands off" experimental control of sophiscated experiments on a variety of laboratory equipment including AWGs, digitizers, current sources, etc.

## Installation

**bbndb** can be downloaded from GitHub:

https://github.com/BBN-Q/bbndb/archive/master.zip

Or **bbndb** can be cloned from GitHub to participate in bbndb development:

git clone https://github.com/BBN-Q/bbndb.git

And subsequently installed using pip:

`
cd bbndb    
pip install -e .       
`

which will automatically fetch and install all of the requirement packages. As typical with package managers, this process will execute the package requirements enumerated in setup.py.

## Upgrading your channel library to a new version

We use *alembic* to facilitate migrations. Examining the `url.sqlalchemy` field in *alembic.ini* you can see the database that is being tracked by default.

`
sqlalchemy.url = sqlite:///BBN.sqlite
`

These do not always work with SQLite due to the inability to alter the tables in certain ways. 

In the simplest case alembic can be run as follows:
`bash
alembic upgrade head
`

For information on how to generate your own migrations, please see *alembic/README*.
