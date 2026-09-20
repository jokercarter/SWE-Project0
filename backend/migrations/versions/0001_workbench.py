"""Baseline schema plus an explicit application schema version.

Existing installations are adopted without deleting their content. Main modules
retain idempotent bootstrap for first-run and test environments.
"""
from alembic import op
revision='0001_workbench'
down_revision=None
branch_labels=None
depends_on=None
def upgrade():
    from backend import features, codex_adapter
    op.execute('CREATE INDEX IF NOT EXISTS records_kind_updated ON records(kind,updated)')
    op.execute('CREATE INDEX IF NOT EXISTS messages_chat_id ON messages(chat_id,id)')
def downgrade():
    # Destructive schema rollback is deliberately not performed automatically.
    op.execute('DROP INDEX IF EXISTS records_kind_updated')
    op.execute('DROP INDEX IF EXISTS messages_chat_id')
