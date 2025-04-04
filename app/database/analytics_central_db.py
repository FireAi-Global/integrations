import functools
import logging
import re
import time

from fastapi import Request
from sqlalchemy import create_engine, event, inspect
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy.orm import scoped_session, sessionmaker
from config.env import COMMUNICATION_DATABASE_URL, COMMUNICATION_DATABASE_HOST, COMMUNICATION_DATABASE_NAME

logger = logging.getLogger(__name__)

engine = None
SessionLocal = None
Base = None


class CustomBase:
    __repr_attrs__ = []
    __repr_max_length__ = 15

    @declared_attr
    def __tablename__(self):
        return resolve_table_name(self.__name__)

    def dict(self):
        """Returns a dict representation of a model."""
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    @property
    def _id_str(self):
        ids = inspect(self).identity
        if ids:
            return "-".join([str(x) for x in ids]) if len(ids) > 1 else str(ids[0])
        return "None"

    @property
    def _repr_attrs_str(self):
        max_length = self.__repr_max_length__

        values = []
        single = len(self.__repr_attrs__) == 1
        for key in self.__repr_attrs__:
            if not hasattr(self, key):
                raise KeyError(
                    f"{self.__class__} has incorrect attribute '{key}' in " "__repr__attrs__".format
                )
            value = getattr(self, key)
            wrap_in_quote = isinstance(value, str)

            value = str(value)
            if len(value) > max_length:
                value = value[:max_length] + "..."

            if wrap_in_quote:
                value = f"'{value}'"
            values.append(value if single else f"{key}:{value}")

        return " ".join(values)

    def __repr__(self):
        id_str = ("#" + self._id_str) if self._id_str else ""
        return "<{} {}{}>".format(
            self.__class__.__name__,
            id_str,
            " " + self._repr_attrs_str if self._repr_attrs_str else "",
        )


if COMMUNICATION_DATABASE_HOST is not None and COMMUNICATION_DATABASE_NAME is not None:
    engine = create_engine(COMMUNICATION_DATABASE_URL, pool_size=20)
    SessionLocal = scoped_session(sessionmaker(bind=engine))

    Base = declarative_base(cls=CustomBase)

    @event.listens_for(engine, "before_cursor_execute")
    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        conn.info.setdefault("query_start_time", []).append(time.time())
        logger.debug("Start Query: %s", statement % parameters)

    @event.listens_for(engine, "after_cursor_execute")
    def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        total = time.time() - conn.info["query_start_time"].pop(-1)
        logger.debug("Query Complete!")
        logger.info("Execution Time: %.2fms", total*1000)


def get_comm_db(request: Request):
    db = SessionLocal()
    if request.method != "GET":
        with db.begin():
            yield db
    else:
        yield db
        db.close()


def comm_db_atomic(func):
    def wrapper(*args, **kwargs):
        db = SessionLocal()
        with db.begin():
            return func(db, *args, **kwargs)

    return wrapper


def get_comm_db_atomic():
    db = SessionLocal()
    with db.begin():
        yield db


def get_comm_db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def comm_db_session(func):
    def wrapper(*args, **kwargs):
        with SessionLocal() as db:
            return func(db, *args, **kwargs)

    return wrapper


def resolve_table_name(name):
    """Resolves table names to their mapped names."""
    names = re.split("(?=[A-Z])", name)  # noqa
    return "_".join([x.lower() for x in names if x])


raise_attribute_error = object()


def resolve_attr(obj, attr, default=None):
    """Attempts to access attr via dotted notation, returns none if attr does not exist."""
    try:
        return functools.reduce(getattr, attr.split("."), obj)
    except AttributeError:
        return default
