"""Explicit migrations; application startup never changes the database schema."""
import os
from alembic import context
from sqlalchemy import create_engine, pool

from pathlib import Path
url = (Path(os.environ['DATABASE_URL_FILE']).read_text().strip()
       if os.getenv('DATABASE_URL_FILE') else os.environ['DATABASE_URL'])
if url.startswith('postgresql://'):
    url = url.replace('postgresql://', 'postgresql+psycopg://', 1)
if context.is_offline_mode():
    context.configure(url=url, literal_binds=True, dialect_opts={'paramstyle': 'named'})
    with context.begin_transaction():
        context.run_migrations()
else:
    engine = create_engine(url, poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(connection=connection)
        with context.begin_transaction():
            # Serialize concurrent migrators in this database.
            connection.exec_driver_sql('SELECT pg_advisory_xact_lock(130013)')
            context.run_migrations()
