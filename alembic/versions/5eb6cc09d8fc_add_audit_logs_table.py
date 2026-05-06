"""bridge missing audit_logs revision

Revision ID: 5eb6cc09d8fc
Revises: 07021a0d1433
Create Date: 2026-05-06 13:29:30.226118

"""
from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = '5eb6cc09d8fc'
down_revision: Union[str, None] = '07021a0d1433'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # This revision existed in the database history but its file was missing.
    # Keep it as a no-op bridge so later revisions can upgrade cleanly.
    pass


def downgrade() -> None:
    pass
