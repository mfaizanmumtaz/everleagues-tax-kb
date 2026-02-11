"""Initialize database tables using SQLAlchemy create_all()."""

from app.database.connection import init_db

try:
    init_db()
    print("Database tables created successfully!")
except Exception as e:
    print(f"Error creating database tables: {e}")
    raise
