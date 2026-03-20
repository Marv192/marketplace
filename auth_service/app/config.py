import os

import redis.asyncio as aioredis

DUMMY_DB_URL = 'postgresql+asyncpg://user:pass@localhost:5432/testdb'
DATABASE_URL = os.getenv("DATABASE_URL", DUMMY_DB_URL)
MIGRATION_DATABASE_URL = os.getenv("MIGRATION_DATABASE_URL", DUMMY_DB_URL)

redis_client = aioredis.Redis(host=os.environ.get('REDIS_HOST'), port=6379, decode_responses=True)
JWT_SECRET = os.getenv('JWT_SECRET')
JWT_ALGORITHM = 'HS256'