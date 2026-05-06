from prometheus_client import Counter


redis_ops = Counter('redis_ops', 'Total Redis operations', ['operation', 'status'])
