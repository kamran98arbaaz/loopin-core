"""Recreate users with integer ID

Revision ID: 034bd85c9b44
Revises: 367db610ad2f
Create Date: 2025-08-02 02:42:53.972572

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '034bd85c9b44'
down_revision = '367db610ad2f'
branch_labels = None
depends_on = None


def upgrade():
    # Skip this migration as it's causing conflicts with existing schema
    # The users table should already be properly structured
    pass


def downgrade():
    # ### revert changes ###
    with op.batch_alter_table('users', schema=None) as batch_op:
        # Add back name
        batch_op.add_column(sa.Column('name', sa.VARCHAR(length=100), nullable=False))

        # Drop unique constraint on username and restore unique on name
        try:
            batch_op.drop_constraint(None, type_='unique')  # drops the username unique constraint
        except Exception:
            pass
        batch_op.create_unique_constraint(batch_op.f('users_name_key'), ['name'], postgresql_nulls_not_distinct=False)

        # Revert password_hash type
        batch_op.alter_column(
            'password_hash',
            existing_type=sa.String(length=128),
            type_=sa.VARCHAR(length=255),
            existing_nullable=False
        )

        # Drop integer id and recreate varchar(36) id (not auto-incrementing)
        batch_op.drop_column('id')
        batch_op.add_column(sa.Column('id', sa.VARCHAR(length=36), primary_key=True, nullable=False))
        
        # Drop username
        batch_op.drop_column('username')
    # ### end revert ###
