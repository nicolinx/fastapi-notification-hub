from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

# Fixed names for constraints and indexes. Without this, Postgres invents names,
# and Alembic cannot reliably alter or drop them in later migrations.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Parent of every ORM model.

    `Base.metadata` knows all tables, and Alembic reads it to build migrations.
    """

    metadata = MetaData(naming_convention=NAMING_CONVENTION)
