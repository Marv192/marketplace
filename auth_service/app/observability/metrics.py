from prometheus_client import Counter, Histogram

redis_ops = Counter('redis_ops', 'Total Redis operations', ['operation', 'status'])

redis_latency = Histogram('redis_latency', 'Redis latency', ['operation'],
                          buckets=(0.0005, 0.001, 0.0025, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25))