from __future__ import annotations

import argparse
import os

from sqlalchemy import select

from app.config import Settings
from app.database import Base, Database
from app.models import AdminTelegramUser, AdminUser
from app.security import hash_password


def bootstrap(settings: Settings, create_schema: bool = False) -> None:
    settings.validate()
    database = Database(settings)
    if create_schema:
        Base.metadata.create_all(database.engine)
    with database.session_factory() as db:
        admin = db.scalar(select(AdminUser).where(AdminUser.username == settings.admin_username))
        if admin is None:
            db.add(
                AdminUser(
                    username=settings.admin_username,
                    password_hash=hash_password(settings.admin_password),
                )
            )
            print(f"Created dashboard admin: {settings.admin_username}")
        # Never overwrite an existing password during a container restart.
        # The administrator can change it safely from the dashboard.
        if settings.bootstrap_admin_telegram_id:
            telegram_admin = db.get(AdminTelegramUser, settings.bootstrap_admin_telegram_id)
            if telegram_admin is None:
                db.add(
                    AdminTelegramUser(
                        telegram_id=settings.bootstrap_admin_telegram_id,
                        role="admin",
                    )
                )
                print(f"Created Telegram admin: {settings.bootstrap_admin_telegram_id}")
        db.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description="Remote Server maintenance CLI")
    parser.add_argument("command", choices=["bootstrap", "init-db", "credentials"])
    args = parser.parse_args()
    settings = Settings.from_env()
    if args.command == "credentials":
        from pathlib import Path

        credentials_file = Path(os.getenv("INITIAL_CREDENTIALS_FILE", "/data/INITIAL_ADMIN_CREDENTIALS.txt"))
        if credentials_file.exists():
            print(credentials_file.read_text(encoding="utf-8"))
        else:
            print("Kredensial awal tidak tersedia. Password mungkin sudah diubah dari dashboard.")
        return
    bootstrap(settings, create_schema=args.command == "init-db")


if __name__ == "__main__":
    main()
