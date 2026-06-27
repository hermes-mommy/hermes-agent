"""P22 round-2 DB verification (read-only)."""
import asyncio
import asyncpg
import os
import re
import pathlib


def load_env():
    """Load env from .env.core without leaking values."""
    env = {}
    env_path = pathlib.Path("/home/guinevere/code/guinevere/.env.core")
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            m = re.match(r"^([A-Z_][A-Z0-9_]*)=(.*)$", line.strip())
            if m:
                env[m.group(1)] = m.group(2)
    return env


async def main():
    env = load_env()
    db_url = env.get("DATABASE_URL", "")
    # Parse "postgresql+asyncpg://user:password@host:port/db"
    m = re.match(r"^postgresql(?:\+asyncpg)?://([^:]+):([^@]+)@([^:/]+):(\d+)/(.+)$", db_url)
    if not m:
        print("Could not parse DATABASE_URL")
        return
    db_user, db_pw, db_host, db_port, db_name = m.groups()
    # Sanity: usernames/hostnames only
    print(f"# connecting to {db_host}:{db_port}/{db_name} as user {db_user[:4]}***")
    # Build connection string without leaking
    conn_str = f"postgresql://{db_user}:{db_pw}@localhost:{db_port}/{db_name}"
    conn = await asyncpg.connect(conn_str)
    print("=== ops.alembic_version ===")
    rows = await conn.fetch("SELECT version_num FROM ops.alembic_version ORDER BY version_num")
    for r in rows:
        print(f"  {r['version_num']}")

    print("\n=== p22 schema tables ===")
    rows = await conn.fetch(
        "SELECT tablename FROM pg_tables WHERE schemaname='p22' ORDER BY tablename"
    )
    for r in rows:
        print(f"  p22.{r['tablename']}")

    print("\n=== p22.integration_registry row count ===")
    cnt = await conn.fetchval("SELECT count(*) FROM p22.integration_registry")
    print(f"  {cnt} rows")

    print("\n=== audit.integration_api_log exists & row count ===")
    exists = await conn.fetchval(
        "SELECT count(*) FROM pg_tables WHERE schemaname='audit' AND tablename='integration_api_log'"
    )
    print(f"  exists: {exists > 0}")
    if exists > 0:
        cnt = await conn.fetchval("SELECT count(*) FROM audit.integration_api_log")
        print(f"  rows: {cnt}")

    print("\n=== guinevere_core user grants on p22.* ===")
    rows = await conn.fetch(
        "SELECT privilege_type FROM information_schema.role_table_grants "
        "WHERE grantee = 'guinevere_core' AND table_schema = 'p22' "
        "AND table_name = 'integration_registry'"
    )
    privs = sorted(set(r["privilege_type"] for r in rows))
    print(f"  p22.integration_registry grantee=guinevere_core: {privs}")

    print("\n=== project_id/project_scope column presence ===")
    rows = await conn.fetch(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema='p22' AND table_name='integration_registry' "
        "AND column_name IN ('project_id','project_scope','adapter_id','created_at','updated_at')"
    )
    for r in rows:
        print(f"  {r['column_name']}")

    # Check actual column list
    print("\n=== full p22.integration_registry columns ===")
    rows = await conn.fetch(
        "SELECT column_name, data_type FROM information_schema.columns "
        "WHERE table_schema='p22' AND table_name='integration_registry' "
        "ORDER BY ordinal_position"
    )
    for r in rows:
        print(f"  {r['column_name']} ({r['data_type']})")

    print("\n=== audit.integration_api_log columns ===")
    rows = await conn.fetch(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema='audit' AND table_name='integration_api_log' "
        "ORDER BY ordinal_position"
    )
    for r in rows:
        print(f"  {r['column_name']}")

    await conn.close()


asyncio.run(main())
