# BBNDB

Configuration database for BBN Qubit Measurement Framework. Used by both Auspex and QGL as a shared, versioned, means of storing instrument, qubit, and filter configurations. Based on SQLAlchemy framework.

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