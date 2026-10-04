from alembic import context
from apexdefend.config import Settings
from apexdefend.db import Base, Database

database = Database(context.config.attributes.get("settings") or Settings())
with database.engine.connect() as connection:
    context.configure(connection=connection, target_metadata=Base.metadata, render_as_batch=True)
    with context.begin_transaction():
        context.run_migrations()
