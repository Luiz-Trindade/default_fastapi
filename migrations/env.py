from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
from sqlmodel import SQLModel
from config import engine  # seu engine do SQLModel
from models.user import User  # importe todos os models aqui

# Alembic configura logging
fileConfig(context.config.config_file_name)

target_metadata = SQLModel.metadata  # metadata do SQLModel

def run_migrations_offline():
    url = str(engine.url)
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    connectable = engine
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
