"""
Run once after creating the MySQL database (via schema.sql) to:
1. Create all tables via SQLAlchemy (safe if you already ran schema.sql)
2. Create a default admin staff account
3. Seed a couple of example hosts

Usage:
    python scripts/init_db.py
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app
from extensions import db
from models import Staff, Host

app = create_app()

with app.app_context():
    db.create_all()

    if not Staff.query.filter_by(username="admin").first():
        admin = Staff(username="admin", name="Administrator", role="admin")
        admin.set_password("admin123")  # CHANGE THIS after first login
        db.session.add(admin)
        print("Created default admin -> username: admin / password: admin123")
    else:
        print("Admin already exists, skipping.")

    if Host.query.count() == 0:
        db.session.add_all([
            Host(name="Priya Sharma", email="priya@example.com", department="Engineering"),
            Host(name="Rahul Verma", email="rahul@example.com", department="HR"),
        ])
        print("Seeded example hosts.")

    db.session.commit()
    print("Database initialized.")
