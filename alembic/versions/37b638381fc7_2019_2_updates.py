"""2019.2 Updates

Revision ID: 37b638381fc7
Revises: fca3f9522922
Create Date: 2019-10-28 15:05:57.218996

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '37b638381fc7'
down_revision = 'fca3f9522922'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('dcsource', sa.Column('qubit_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'dcsource', 'qubit', ['qubit_id'], ['id'])
    op.add_column('edge', sa.Column('cnot_impl', sa.String(), nullable=True))
    op.add_column('qubit', sa.Column('bias_pairs', sa.PickleType(), nullable=True))
    op.drop_column('transmitter', 'delay')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('transmitter', sa.Column('delay', sa.FLOAT(), nullable=False))
    op.drop_column('qubit', 'bias_pairs')
    op.drop_column('edge', 'cnot_impl')
    op.drop_constraint(None, 'dcsource', type_='foreignkey')
    op.drop_column('dcsource', 'qubit_id')
    # ### end Alembic commands ###
