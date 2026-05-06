"""add audit_logs table

Revision ID: fa1808d37dda
Revises: 5eb6cc09d8fc
Create Date: 2026-05-06 13:35:36.889956

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'fa1808d37dda'
down_revision: Union[str, None] = '5eb6cc09d8fc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('audit_logs',
    sa.Column('company_id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=True),
    sa.Column('action', sa.String(length=100), nullable=False),
    sa.Column('ip_address', sa.String(length=45), nullable=True),
    sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_audit_company_timestamp', 'audit_logs', ['company_id', 'timestamp'], unique=False)
    op.create_index('idx_audit_action', 'audit_logs', ['action'], unique=False)
    op.create_index('ix_audit_logs_user_id', 'audit_logs', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_audit_logs_user_id'), table_name='audit_logs')
    op.drop_index('idx_audit_action', table_name='audit_logs')
    op.drop_index('idx_audit_company_timestamp', table_name='audit_logs')
    op.drop_table('audit_logs')
