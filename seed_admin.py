import os

from dotenv import load_dotenv

from auth import hash_password
from database import SessionLocal
from models import User


load_dotenv()


def seed_admin():
    username = os.getenv("ADMIN_USERNAME")
    email = os.getenv("ADMIN_EMAIL")
    password = os.getenv("ADMIN_PASSWORD")

    if not username or not email or not password:
        raise ValueError(
            "ADMIN_USERNAME, ADMIN_EMAIL and ADMIN_PASSWORD must be set"
        )

    db = SessionLocal()

    try:
        existing_user = db.query(User).filter(
            User.username == username
        ).first()

        if existing_user is not None:
            existing_user.email = email
            existing_user.hashed_password = hash_password(password)
            existing_user.role = "admin"

            db.commit()

            print(f"Admin user '{username}' updated.")
            return

        admin = User(
            username=username,
            email=email,
            hashed_password=hash_password(password),
            role="admin"
        )

        db.add(admin)
        db.commit()

        print(f"Admin user '{username}' created.")

    finally:
        db.close()


if __name__ == "__main__":
    seed_admin()