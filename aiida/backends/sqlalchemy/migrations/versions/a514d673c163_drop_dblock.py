"""Drop the DbLock model

Revision ID: a514d673c163
Revises: f9a69de76a9a
Create Date: 2018-05-10 19:08:51.780194

"""
from alembic import op
from sqlalchemy.dialects import postgresql
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a514d673c163'
down_revision = 'f9a69de76a9a'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_table('db_dblock')


def downgrade():
    op.create_table('db_dblock',
    sa.Column('key', sa.VARCHAR(length=255), autoincrement=False, nullable=False),
    sa.Column('creation', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=True),
    sa.Column('timeout', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('owner', sa.VARCHAR(length=255), autoincrement=False, nullable=True),
    sa.PrimaryKeyConstraint('key', name=u'db_dblock_pkey')
    )
