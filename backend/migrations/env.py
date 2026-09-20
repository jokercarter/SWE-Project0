from alembic import context
from backend.main import engine
def run():
    with engine.connect() as connection:
        context.configure(connection=connection)
        with context.begin_transaction():context.run_migrations()
run()
