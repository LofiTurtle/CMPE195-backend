"""Add unique contstraint

Revision ID: 9563ebbfe500
Revises: 0af398ca8466
Create Date: 2024-11-21 23:12:47.826453

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9563ebbfe500'
down_revision = '0af398ca8466'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('rating_field', schema=None) as batch_op:
        batch_op.create_unique_constraint(batch_op.f('uq_rating_field_rating_id'), ['rating_id', 'name'])

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('rating_field', schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f('uq_rating_field_rating_id'), type_='unique')

    # ### end Alembic commands ###
