Alembic is used to upgrade any previous database versions to accomodate changes to the schema.

We assume that the database is located at bbndb/BBN.sqlite (where bbndb is the base directory of the package not the source directory.)

For migrating c.f.:
https://alembic.sqlalchemy.org/en/latest/autogenerate.html

For merging c.f.:
https://alembic.sqlalchemy.org/en/latest/branches.html#merging-branches

When submitting a pull request it will be helpful to indicate whether any migrations are performed.

To create new revisions automatically start with the old version of the database in `BBN.sqlite` (or other database, as set in alembic.ini).
You may have to stamp the head  revision by:

`alembic stamp head`

Then run alembic in the new version:

`git checkout` \<new branch\>

`alembic revision --autogenerate -m` "brief notes on update" # Create the diff

You may need to modify the alembic version table in the database manually.

`git add alembic/versions/abcabc123123_brief_notes_on_update.py` # add to version control

To apply:
`alembic upgrade head`

You can experiment with migration using this sample database as a starting point:

`python alembic/fill_db.py`
