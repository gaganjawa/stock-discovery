"""Explicit private bootstrap after migrations; never called by runtime startup."""
import psycopg
from psycopg import sql
from stock_discovery_analysis.runtime import setting


def configure(conn, password):
    if len(password) < 32:
        raise ValueError("Runtime password must have at least 32 random characters")
    with conn.transaction():
        if not conn.execute("SELECT 1 FROM pg_roles WHERE rolname='stk_runtime'").fetchone():
            conn.execute("CREATE ROLE stk_runtime LOGIN")
        conn.execute(sql.SQL("ALTER ROLE stk_runtime WITH LOGIN NOSUPERUSER NOCREATEDB "
                             "NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD {}")
                     .format(sql.Literal(password)))
        if conn.execute("SELECT 1 FROM pg_auth_members WHERE member=(SELECT oid FROM pg_roles WHERE rolname='stk_runtime')").fetchone():
            raise ValueError("Runtime role must not inherit other roles")
        database = conn.execute("SELECT current_database()").fetchone()[0]
        conn.execute(sql.SQL("REVOKE ALL ON DATABASE {} FROM PUBLIC").format(sql.Identifier(database)))
        conn.execute(sql.SQL("GRANT CONNECT ON DATABASE {} TO stk_runtime").format(sql.Identifier(database)))
        conn.execute("REVOKE CREATE ON SCHEMA public FROM PUBLIC")
        conn.execute("REVOKE ALL ON SCHEMA research FROM PUBLIC, stk_runtime")
        conn.execute("GRANT USAGE ON SCHEMA research TO stk_runtime")
        conn.execute("REVOKE ALL ON ALL TABLES IN SCHEMA research FROM stk_runtime")
        conn.execute("GRANT SELECT, INSERT ON ALL TABLES IN SCHEMA research TO stk_runtime")
        conn.execute("GRANT UPDATE ON research.jobs TO stk_runtime")
        conn.execute("GRANT USAGE ON ALL SEQUENCES IN SCHEMA research TO stk_runtime")
        conn.execute("GRANT SELECT ON public.alembic_version TO stk_runtime")
        # Explicit grants are reapplied by this one-shot service after every migration.


if __name__ == "__main__":
    with psycopg.connect(setting("DATABASE_URL")) as conn:
        configure(conn, setting("RUNTIME_PASSWORD"))
