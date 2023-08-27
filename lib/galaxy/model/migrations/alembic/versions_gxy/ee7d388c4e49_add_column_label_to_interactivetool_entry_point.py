"""add column label to interactivetool_entry_point

Revision ID: ee7d388c4e49
Revises: 987ce9839ecb
Create Date: 2023-08-27 22:13:29.171575

"""
from sqlalchemy import Column, Text

from galaxy.model.migrations.util import (
    add_column,
    drop_column,
)

# revision identifiers, used by Alembic.
revision = "ee7d388c4e49"
down_revision = "987ce9839ecb"
branch_labels = None
depends_on = None

# database object names used in this revision
table_name = "interactivetool_entry_point"
column_name = "label"


def upgrade():
    add_column(table_name, Column(column_name, Text()))


def downgrade():
    drop_column(table_name, column_name)
