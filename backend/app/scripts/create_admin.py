import argparse
from getpass import getpass

from sqlalchemy import select

from app.core.enums import UserRole
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.user import User


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create an initial admin user.")
    parser.add_argument("--username", default="admin")
    parser.add_argument("--password", default=None)
    parser.add_argument("--reset-password", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    password = args.password or getpass("Admin password: ")
    if not password:
        raise SystemExit("Password cannot be empty.")

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.username == args.username))
        if user is not None:
            user.role = UserRole.ADMIN.value
            user.is_active = True
            if args.reset_password:
                user.password_hash = hash_password(password)
            db.commit()
            print(f"Admin user already exists: {args.username}")
            return

        user = User(
            username=args.username,
            password_hash=hash_password(password),
            role=UserRole.ADMIN.value,
            is_active=True,
        )
        db.add(user)
        db.commit()
        print(f"Admin user created: {args.username}")


if __name__ == "__main__":
    main()

