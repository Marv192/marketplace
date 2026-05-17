import logging
import sys

from pythonjsonlogger.json import JsonFormatter


class ServiceFilter(logging.Filter):
    def __init__(self, service: str):
        super().__init__()
        self.service = service

    def filter(self, record):
        record.service = self.service
        return True


def setup_json_logging(service: str = "auth"):
    root_logger = logging.getLogger()

    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    formatter = JsonFormatter('%(asctime)s %(levelname)s %(service)s %(message)s',
                                         rename_fields={
                                             "asctime": "timestamp",
                                             "levelname": "level"
                                         },
                                datefmt='%Y-%m-%dT%H:%M:%SZ',
                                json_default=str)

    handler.setFormatter(formatter)
    handler.addFilter(ServiceFilter(service=service))
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)
    root_logger.propagate = False

    sqlalchemy_engine = logging.getLogger("sqlalchemy.engine")
    sqlalchemy_engine.setLevel(logging.ERROR)
    sqlalchemy_engine.propagate = False

    sqlalchemy_pool = logging.getLogger("sqlalchemy.pool")
    sqlalchemy_pool.setLevel(logging.ERROR)
    sqlalchemy_pool.propagate = False

    alembic_logger = logging.getLogger("alembic")
    alembic_logger.setLevel(logging.ERROR)
    alembic_logger.propagate = False

    uvicorn_access = logging.getLogger("uvicorn.access")
    uvicorn_access.setLevel(logging.ERROR)
    uvicorn_access.propagate = False

