from app import app, db

with app.app_context():
    db.create_all()
    print("✅ init_db.py: Tables created successfully")
