import sqlalchemy as sa
from app import create_app, db
from sqlalchemy import text

app = create_app()


def reset_database():
    with app.app_context():
        print("Starting database reset...")

        # 1. Drop all tables defined in models
        print("Dropping application tables...")
        db.drop_all()
        print("Application tables dropped.")

        # 2. Explicitly drop alembic_version if it exists
        # (It's not usually in db.metadata)
        engine = db.engine
        inspector = sa.inspect(engine)
        if "alembic_version" in inspector.get_table_names():
            print("Dropping alembic_version table...")
            with engine.connect() as conn:
                conn.execute(text("DROP TABLE alembic_version"))
                conn.commit()
            print("alembic_version table dropped.")
        else:
            print("alembic_version table not found.")

        print("Database reset complete. You can now run 'flask db upgrade'.")


if __name__ == "__main__":
    reset_database()
