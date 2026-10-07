"""Very small SQLite migration helper.

`Base.metadata.create_all()` only creates tables that don't exist yet — it
never adds columns to a table that's already there. Since this app ships as
a desktop exe with a real per-user SQLite file that outlives each update,
every time a column is added to a model it must also be added here, or
existing installs crash on the first request that touches the new column.
"""
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.sql.schema import MetaData


def run_lightweight_migrations(engine: Engine, metadata: MetaData) -> None:
    inspector = inspect(engine)
    with engine.begin() as conn:
        for table in metadata.sorted_tables:
            if not inspector.has_table(table.name):
                continue  # brand-new table: create_all already made it in full
            existing_columns = {c["name"] for c in inspector.get_columns(table.name)}
            for column in table.columns:
                if column.name in existing_columns:
                    continue
                ddl_type = column.type.compile(dialect=engine.dialect)
                stmt = f'ALTER TABLE "{table.name}" ADD COLUMN "{column.name}" {ddl_type}'
                if column.default is not None and getattr(column.default, "is_scalar", False):
                    default_val = column.default.arg
                    if isinstance(default_val, bool):
                        default_val = 1 if default_val else 0
                    if isinstance(default_val, str):
                        stmt += f" DEFAULT '{default_val}'"
                    else:
                        stmt += f" DEFAULT {default_val}"
                conn.execute(text(stmt))
