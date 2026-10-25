"""STK-042/059/060: join D3-11 and the installed REAL-001 history.

Main retains 0012. REAL's shadow ancestor is now real_0012; installed REAL
databases at 0013 already contain its schema. They apply only D3-11's 0012
before this merge. No stamping, data copy or replacement is required.
"""
revision = '0014'
down_revision = ('0012', '0013')
branch_labels = depends_on = None


def upgrade():
    pass


def downgrade():
    pass
