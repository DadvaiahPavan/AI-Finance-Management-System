#!/usr/bin/env python3
"""
Database initialization script for AI Finance Management System
"""

import os
import sys

# Add the project directory to the Python path
sys.path.insert(0, os.path.dirname(__file__))

try:
    from app import app, db
    
    def init_database():
        """Initialize the database with all required tables"""
        try:
            with app.app_context():
                # Create all tables
                db.create_all()
                print("✅ Database tables created successfully")
                
                # Verify tables were created
                from sqlalchemy import inspect
                inspector = inspect(db.engine)
                tables = inspector.get_table_names()
                print(f"✅ Created tables: {tables}")
                
                return True
        except Exception as e:
            print(f"❌ Error creating database tables: {str(e)}")
            return False
    
    if __name__ == "__main__":
        success = init_database()
        if success:
            print("✅ Database initialization completed successfully")
            sys.exit(0)
        else:
            print("❌ Database initialization failed")
            sys.exit(1)
    else:
        # When imported, just run the initialization
        init_database()

except ImportError as e:
    print(f"❌ Import error: {str(e)}")
    print("Make sure app.py is in the same directory and all dependencies are installed")
    sys.exit(1)
except Exception as e:
    print(f"❌ Unexpected error: {str(e)}")
    sys.exit(1)

