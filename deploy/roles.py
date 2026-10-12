"""Explicit private bootstrap after migrations; never called by runtime startup."""
import psycopg
from psycopg import sql
from stock_discovery_analysis.runtime import setting


def configure(conn, password, role="stk_runtime"):
    if len(password) < 32:
        raise ValueError("Runtime password must have at least 32 random characters")
    database = conn.execute("SELECT current_database()").fetchone()[0]
    if role != "stk_runtime" and not (database == "stk013_test" and role.startswith("stk_test_")):
        raise ValueError("Alternate roles are restricted to the disposable test database")
    identifier = sql.Identifier(role)
    with conn.transaction():
        if not conn.execute("SELECT 1 FROM pg_roles WHERE rolname=%s", (role,)).fetchone():
            conn.execute(sql.SQL("CREATE ROLE {} LOGIN").format(identifier))
        conn.execute(sql.SQL("ALTER ROLE {} WITH LOGIN NOSUPERUSER NOCREATEDB "
                             "NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD {}")
                     .format(identifier, sql.Literal(password)))
        if conn.execute("SELECT 1 FROM pg_auth_members WHERE member=(SELECT oid FROM pg_roles WHERE rolname=%s)", (role,)).fetchone():
            raise ValueError("Runtime role must not inherit other roles")
        conn.execute(sql.SQL("REVOKE ALL ON DATABASE {} FROM PUBLIC").format(sql.Identifier(database)))
        conn.execute(sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(sql.Identifier(database), identifier))
        conn.execute("REVOKE CREATE ON SCHEMA public FROM PUBLIC")
        for template in (
            "REVOKE ALL ON SCHEMA research FROM PUBLIC, {}",
            "GRANT USAGE ON SCHEMA research TO {}",
            "REVOKE ALL ON ALL TABLES IN SCHEMA research FROM {}",
            "GRANT SELECT, INSERT ON ALL TABLES IN SCHEMA research TO {}",
            "GRANT UPDATE ON research.jobs TO {}",
            "GRANT USAGE ON ALL SEQUENCES IN SCHEMA research TO {}",
            "GRANT SELECT ON public.alembic_version TO {}",
        ):
            conn.execute(sql.SQL(template).format(identifier))
        # Explicit grants are reapplied by this one-shot service after every migration.


if __name__ == "__main__":
    with psycopg.connect(setting("DATABASE_URL")) as conn:
        configure(conn, setting("RUNTIME_PASSWORD"))
