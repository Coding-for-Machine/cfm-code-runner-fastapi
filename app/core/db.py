import asyncpg

DB_CONFIG = {
    "user": "neondb_owner",
    "password": "npg_y2oRMm5KJkEC",
    "database": "neondb",
    "host": "ep-snowy-cake-a1auh45l-pooler.ap-southeast-1.aws.neon.tech",
    "port": 5432,
    "ssl":"require",
}

# DB_NAME=neondb
# DB_USER=neondb_owner
# DB_PASSWORD=npg_y2oRMm5KJkEC
# DB_HOST=ep-snowy-cake-a1auh45l-pooler.ap-southeast-1.aws.neon.tech
# DB_PORT=5432

# DB_SSLMODE=require

_pool = None

async def get_pool():
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            min_size=1,
            max_size=10,
            **DB_CONFIG
        )
    return _pool