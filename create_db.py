# create_db.py
from app import app, db

with app.app_context():
    db.create_all()
    print("✅ Tables created successfully.")
