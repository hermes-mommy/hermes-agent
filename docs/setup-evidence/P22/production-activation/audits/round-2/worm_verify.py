"""P22 round-2 WORM grant verification (read-only)."""
import asyncio
import asyncpg
import os
import re
import pathlib


def load_env():
    env_path = pathlib.Path("/home/guinevere/code/guinevere/.env.core")
    env = {}
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            m = re.match(r"^([A-Z_][A-Z0-9_]*)=(.*)$", line.strip())
            if m:
                env[m.group(1)] = m.group(2)
    return env


async def main():
    env = load_env()
    db_url = env.get("DATABASE_URL", "")
    m = re.match(r"^postgresql(?:\+asyncpg)?://([^:]+):([^@]+)@([^:/]+):(\d+)/(.+)$", db_url)
    if not m:
        print("Could not parse DATABASE_URL")
        return
    db_user, db_pw, db_host, db_port, db_name = m.groups()

    # Connect as superuser via OS-style auth (postgres) to inspect role grants
    # First try with the DB user we have
    conn_str = f"postgresql://{db_user}:{db_pw}@localhost:{db_port}/{db_name}"
    conn = await asyncpg.connect(conn_str)

    print("=== Who is current user ===")
    cur = await conn.fetchval("SELECT current_user")
    print(f"  current_user: {cur}")

    print("\n=== Roles in DB ===")
    rows = await conn.fetch(
        "SELECT rolname FROM pg_roles WHERE rolname LIKE '%guine%' OR rolname='postgres' ORDER BY rolname"
    )
    for r in rows:
        print(f"  {r['rolname']}")

    print("\n=== p22 integration_registry: all grantees + privileges ===")
    rows = await conn.fetch(
        "SELECT grantee, privilege_type FROM information_schema.role_table_grants "
        "WHERE table_schema='p22' AND table_name='integration_registry' "
        "ORDER BY grantee, privilege_type"
    )
    cur_grantee = None
    for r in rows:
        if r["grantee"] != cur_grantee:
            cur_grantee = r["grantee"]
            print(f"  -- grantee={cur_grantee} --")
        print(f"     {r['privilege_type']}")

    print("\n=== p22 secret_ref_metadata: all grants ===")
    rows = await conn.fetch(
        "SELECT grantee, privilege_type FROM information_schema.role_table_grants "
        "WHERE table_schema='p22' AND table_name='secret_ref_metadata' "
        "ORDER BY grantee, privilege_type"
    )
    cur_grantee = None
    for r in rows:
        if r["grantee"] != cur_grantee:
            cur_grantee = r["grantee"]
            print(f"  -- grantee={cur_grantee} --")
        print(f"     {r['privilege_type']}")

    print("\n=== audit.integration_api_log: grantees ===")
    rows = await conn.fetch(
        "SELECT grantee, privilege_type FROM information_schema.role_table_grants "
        "WHERE table_schema='audit' AND table_name='integration_api_log' "
        "ORDER BY grantee, privilege_type"
    )
    cur_grantee = None
    for r in rows:
        if r["grantee"] != cur_grantee:
            cur_grantee = r["grantee"]
            print(f"  -- grantee={cur_grantee} --")
        print(f"     {r['privilege_type']}")

    print("\n=== Triggers on audit.integration_api_log ===")
    rows = await conn.fetch(
        "SELECT trigger_name, event_manipulation, action_timing, action_statement "
        "FROM information_schema.triggers WHERE event_object_schema='audit' "
        "AND event_object_table='integration_api_log'"
    )
    for r in rows:
        print(f"  {r['trigger_name']} ({r['action_timing']} {r['event_manipulation']})")

    print("\n=== RLS (row-level security) enabled? ===")
    rows = await conn.fetch(
        "SELECT schemaname, tablename, rowsecurity FROM pg_tables "
        "WHERE schemaname IN ('p22','audit') AND tablename IN ('integration_registry','secret_ref_metadata','integration_api_log')"
    )
    for r in rows:
        print(f"  {r['schemaname']}.{r['tablename']}: rowsecurity={r['rowsecurity']}")

    await conn.close()


asyncio.run(main())
