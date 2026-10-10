"""Initial research storage. Immutability policy belongs to STK-015."""
from pathlib import Path
from alembic import op

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    sql = Path(__file__).with_suffix('.sql').read_text()
    op.execute(sql)


def downgrade():
    for table in ('trade_outcomes', 'forecast_outcomes', 'decisions', 'contribution_ledger',
                  'holdings', 'capital_buckets', 'accounts', 'runs', 'facts',
                  'documents', 'candles', 'instrument_symbols', 'instruments'):
        op.execute(f'DROP TABLE research.{table}')
    op.execute('DROP FUNCTION research.validate_ledger_reversal()')
    op.execute('DROP SCHEMA research')
