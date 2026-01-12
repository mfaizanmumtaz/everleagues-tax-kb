"""Initialize database tables using SQLAlchemy create_all()."""

from app.database.connection import init_db

if __name__ == "__main__":
    print("Creating database tables...")
    print("This will create all tables defined in db_models/")
    try:
        init_db()
        print("Database tables created successfully!")
    except Exception as e:
        print(f"Error creating database tables: {e}")
        raise

