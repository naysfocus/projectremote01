from __future__ import annotations

import json
import logging
from pathlib import Path

from sqlalchemy import select
from telegram import (
    BotCommand,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    Update,
)
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from app.config import Settings
from app.database import Database
from app.integration_store import get_or_create_config, get_secrets
from app.models import ActivationKey, AdminTelegramUser, NotificationOutbox, SuspicionEvent
from app.services.admin import (
    create_activation_key,
    expire_pending_keys,
    get_device_detail,
    list_devices,
    review_suspicion,
    set_authorization_status,
    stats_summary,
)
from app.status_files import read_json
from app.utils import as_utc, local_display, utcnow

LOGGER = logging.getLogger("telegram_bot")
SETTINGS = Settings.from_env()
DATABASE = Database(SETTINGS)

BTN_NEW_KEY = "🔑 Buat Kode Aktivasi"
BTN_STATUS = "📊 Status Sistem"
BTN_DEVICES = "💻 Device"
BTN_KEYS = "🧾 Kode Aktif"
BTN_SECURITY = "⚠️ Keamanan"
BTN_MENU = "🏠 Menu Utama"


def _main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [BTN_NEW_KEY],
            [BTN_STATUS, BTN_DEVICES],
            [BTN_KEYS, BTN_SECURITY],
        ],
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Pilih menu Remote Server",
    )


def _admin(telegram_id: int) -> AdminTelegramUser | None:
    with DATABASE.session_factory() as db:
        return db.get(AdminTelegramUser, str(telegram_id))


async def _require_role(update: Update, role: str = "viewer") -> AdminTelegramUser | None:
    user = update.effective_user
    if user is None:
        return None
    admin = _admin(user.id)
    if admin is None:
        if update.effective_message:
            await update.effective_message.reply_text("Akun Telegram ini belum dipasangkan ke server.")
        return None
    if role == "admin" and admin.role != "admin":
        if update.effective_message:
            await update.effective_message.reply_text("Akses ini hanya untuk admin.")
        return None
    return admin


def _app_label(app_type: str) -> str:
    return "Video Mixer" if app_type == "matrix_generator" else "Remote HP"


async def _send_menu(update: Update, text: str = "Pilih menu yang diperlukan:") -> None:
    if update.effective_message:
        await update.effective_message.reply_text(text, reply_markup=_main_menu())


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    message = update.effective_message
    if user is None or message is None:
        return
    admin = _admin(user.id)
    if admin is not None:
        await _send_menu(update, f"Halo. Status Anda: {admin.role} ✅")
        return
    supplied_code = context.args[0].strip() if context.args else ""
    with DATABASE.session_factory() as db:
        config = get_or_create_config(db)
        expires_at = as_utc(config.telegram_pair_expires_at)
        if (
            supplied_code
            and config.telegram_pair_code
            and supplied_code == config.telegram_pair_code
            and expires_at is not None
            and expires_at > utcnow()
        ):
            existing = db.get(AdminTelegramUser, str(user.id))
            if existing is None:
                db.add(
                    AdminTelegramUser(
                        telegram_id=str(user.id),
                        telegram_username=user.username,
                        role="admin",
                    )
                )
            config.telegram_admin_id = str(user.id)
            config.telegram_pair_code = None
            config.telegram_pair_expires_at = None
            config.revision += 1
            config.updated_at = utcnow()
            db.commit()
            await _send_menu(update, "✅ Telegram berhasil dipasangkan sebagai admin Remote Server.")
            return
    await message.reply_text(
        "Bot belum dipasangkan. Masukkan kode dari menu Integrasi, contoh: /start 12345678"
    )


async def menu(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _require_role(update):
        return
    await _send_menu(update)


async def newkey(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _require_role(update, "admin") or not update.effective_message:
        return
    keyboard = [[
        InlineKeyboardButton("🎬 Video Mixer", callback_data="newkey:matrix_generator"),
        InlineKeyboardButton("📱 Remote HP", callback_data="newkey:remote_hp"),
    ]]
    await update.effective_message.reply_text(
        "Pilih aplikasi. Kode akan berlaku selama 1 jam:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def newkey_callback(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None or update.effective_user is None:
        return
    if not await _require_role(update, "admin"):
        await query.answer("Tidak diizinkan", show_alert=True)
        return
    await query.answer()
    _, app_type = (query.data or "").split(":", 1)
    with DATABASE.session_factory() as db:
        key = create_activation_key(
            db,
            app_type=app_type,
            expires_in_hours=1,
            telegram_id=str(update.effective_user.id),
        )
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("❌ Batalkan kode", callback_data=f"cancelkey:{key.code}")]]
    )
    await query.edit_message_text(
        f"✅ Kode aktivasi {_app_label(app_type)}\n\n"
        f"<code>{key.code}</code>\n\n"
        f"Berlaku 1 jam, sampai: {local_display(key.expires_at, SETTINGS.display_timezone)}",
        parse_mode="HTML",
        reply_markup=keyboard,
    )


async def devices(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _require_role(update) or not update.effective_message:
        return
    with DATABASE.session_factory() as db:
        rows = list_devices(db, SETTINGS)
    if not rows:
        await update.effective_message.reply_text("Belum ada device.", reply_markup=_main_menu())
        return
    lines = []
    buttons = []
    for row in rows[:20]:
        marker = "🟢" if row["is_online"] else "⚫"
        warning = f" ⚠️{row['unreviewed_suspicion_count']}" if row["unreviewed_suspicion_count"] else ""
        lines.append(f"{marker} #{row['id']} {row['label']}{warning}")
        buttons.append([InlineKeyboardButton(f"Buka #{row['id']} · {row['label']}", callback_data=f"device:{row['id']}")])
    await update.effective_message.reply_text(
        "Daftar device:\n\n" + "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def _send_device_detail(message, device_id: int) -> None:  # type: ignore[no-untyped-def]
    with DATABASE.session_factory() as db:
        data = get_device_detail(db, device_id, SETTINGS)
    if data is None:
        await message.reply_text("Device tidak ditemukan.")
        return
    lines = [
        f"💻 #{data['id']} {data['label']}",
        f"Status: {'online' if data['is_online'] else 'offline'}",
        f"OS: {data['os_info'] or data['os_type'] or '-'}",
        f"Terakhir aktif: {data['last_seen_at'] or '-'}",
    ]
    for auth in data["authorizations"]:
        lines.append(
            f"{_app_label(auth['app_type'])}: {auth['status']} | "
            f"{'online' if auth['is_online'] else 'offline'} | versi {auth['app_version'] or '-'}"
        )
    await message.reply_text("\n".join(lines))


async def device_detail(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _require_role(update) or not update.effective_message:
        return
    if not context.args or not context.args[0].isdigit():
        await update.effective_message.reply_text("Format: /device <id>")
        return
    await _send_device_detail(update.effective_message, int(context.args[0]))


async def device_callback(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None or not await _require_role(update):
        return
    await query.answer()
    raw_id = (query.data or "").split(":", 1)[1]
    if not raw_id.isdigit():
        await query.answer("ID tidak valid", show_alert=True)
        return
    await _send_device_detail(query.message, int(raw_id))


async def pending(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _require_role(update) or not update.effective_message:
        return
    with DATABASE.session_factory() as db:
        expire_pending_keys(db)
        rows = db.scalars(
            select(ActivationKey)
            .where(ActivationKey.status == "pending")
            .order_by(ActivationKey.created_at.desc())
            .limit(20)
        ).all()
    if not rows:
        await update.effective_message.reply_text("Tidak ada kode aktif.", reply_markup=_main_menu())
        return
    for key in rows:
        markup = InlineKeyboardMarkup(
            [[InlineKeyboardButton("❌ Batalkan", callback_data=f"cancelkey:{key.code}")]]
        )
        await update.effective_message.reply_text(
            f"<code>{key.code}</code> · {_app_label(key.app_type)}\nBerlaku sampai: {local_display(key.expires_at, SETTINGS.display_timezone)}",
            parse_mode="HTML",
            reply_markup=markup,
        )


async def cancelkey(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _require_role(update, "admin") or not update.effective_message:
        return
    if not context.args:
        await update.effective_message.reply_text("Format: /cancelkey <kode>")
        return
    await _cancel_code(update.effective_message, context.args[0].strip().upper())


async def _cancel_code(message, code: str) -> None:  # type: ignore[no-untyped-def]
    with DATABASE.session_factory() as db:
        key = db.scalar(select(ActivationKey).where(ActivationKey.code == code))
        if key is None:
            await message.reply_text("Kode tidak ditemukan.")
            return
        if key.status != "pending":
            await message.reply_text(f"Kode berstatus {key.status}, tidak dapat dibatalkan.")
            return
        key.status = "cancelled"
        db.commit()
    await message.reply_text(f"Kode {code} dibatalkan.")


async def cancelkey_callback(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None or not await _require_role(update, "admin"):
        return
    code = (query.data or "").split(":", 1)[1].upper()
    with DATABASE.session_factory() as db:
        key = db.scalar(select(ActivationKey).where(ActivationKey.code == code))
        if key is None or key.status != "pending":
            await query.answer("Kode tidak aktif", show_alert=True)
            return
        key.status = "cancelled"
        db.commit()
    await query.answer("Kode dibatalkan")
    await query.edit_message_reply_markup(reply_markup=None)


async def _authorization_command(update: Update, context: ContextTypes.DEFAULT_TYPE, status: str) -> None:
    if not await _require_role(update, "admin") or not update.effective_message:
        return
    if len(context.args) < 2 or not context.args[0].isdigit():
        cmd = "revoke" if status == "revoked" else "reactivate"
        await update.effective_message.reply_text(
            f"Format: /{cmd} <device_id> <matrix_generator|remote_hp|all>"
        )
        return
    device_id = int(context.args[0])
    selected = context.args[1].lower()
    app_types = ["matrix_generator", "remote_hp"] if selected == "all" else [selected]
    if any(item not in {"matrix_generator", "remote_hp"} for item in app_types):
        await update.effective_message.reply_text("Jenis aplikasi tidak valid.")
        return
    changed = []
    with DATABASE.session_factory() as db:
        for app_type in app_types:
            result = set_authorization_status(
                db,
                device_id=device_id,
                app_type=app_type,
                status=status,
                actor_type="telegram",
                actor_id=str(update.effective_user.id),
            )
            if result:
                changed.append(_app_label(app_type))
    if not changed:
        await update.effective_message.reply_text("Otorisasi tidak ditemukan.")
        return
    await update.effective_message.reply_text(f"Status {', '.join(changed)} diubah menjadi {status}.")


async def revoke(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _authorization_command(update, context, "revoked")


async def reactivate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _authorization_command(update, context, "active")


async def suspicious(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _require_role(update) or not update.effective_message:
        return
    with DATABASE.session_factory() as db:
        rows = db.scalars(
            select(SuspicionEvent)
            .where(SuspicionEvent.admin_reviewed.is_(False))
            .order_by(SuspicionEvent.detected_at.desc())
            .limit(30)
        ).all()
    if not rows:
        await update.effective_message.reply_text(
            "Tidak ada kecurigaan yang belum ditinjau.", reply_markup=_main_menu()
        )
        return
    for event in rows:
        keyboard = [[
            InlineKeyboardButton("Abaikan", callback_data=f"suspicion:{event.id}:ignored"),
            InlineKeyboardButton("Revoke Device", callback_data=f"suspicion:{event.id}:revoked"),
        ]]
        await update.effective_message.reply_text(
            f"⚠️ Event #{event.id}\nDevice #{event.device_id}\n"
            f"Aplikasi: {_app_label(event.app_type)}\nWaktu: {local_display(event.detected_at, SETTINGS.display_timezone)}",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )


async def suspicion_callback(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None or update.effective_user is None:
        return
    if not await _require_role(update, "admin"):
        await query.answer("Tidak diizinkan", show_alert=True)
        return
    _, raw_id, action = (query.data or "").split(":", 2)
    with DATABASE.session_factory() as db:
        result = review_suspicion(
            db,
            event_id=int(raw_id),
            action=action,
            telegram_id=str(update.effective_user.id),
        )
    if result is None:
        await query.answer("Event tidak ditemukan", show_alert=True)
        return
    await query.answer("Tersimpan")
    await query.edit_message_reply_markup(reply_markup=None)


async def stats(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _require_role(update) or not update.effective_message:
        return
    with DATABASE.session_factory() as db:
        data = stats_summary(db, SETTINGS)
    scheduler = read_json(Path(SETTINGS.data_dir) / "scheduler-status.json")
    integrations = read_json(Path(SETTINGS.data_dir) / "integration-status.json")
    telegram = integrations.get("telegram") or {}
    cloudflare = integrations.get("cloudflare") or {}
    backup_dir = Path(SETTINGS.data_dir) / "backups"
    backups = sorted([item for item in backup_dir.glob("*.sqlite3") if item.name.startswith(("remote-server-", "scaleup-"))], reverse=True)
    lines = [
        "📊 Status Remote Server",
        "Server: aktif ✅",
        f"Scheduler: {'aktif ✅' if scheduler.get('status') == 'ok' else 'perlu dicek ⚠️'}",
        f"Telegram: {'aktif ✅' if telegram.get('running') else 'nonaktif/bermasalah'}",
        f"Cloudflare: {'terhubung ✅' if cloudflare.get('connected') else 'belum terhubung'}",
        f"Backup terakhir: {backups[0].name if backups else 'belum ada'}",
        "",
        f"Total device: {data['total_devices']}",
        f"Sesi online: {data['online_sessions']}",
        f"Video upload hari ini: {data['uploaded_videos_today']}",
        f"Output Video Mixer hari ini: {data['generated_videos_today']}",
        f"Proses aktif: {data['active_jobs']}",
        f"Kecurigaan belum ditinjau: {data['unreviewed_suspicion_events']}",
    ]
    await update.effective_message.reply_text("\n".join(lines), reply_markup=_main_menu())


async def menu_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (update.effective_message.text if update.effective_message else "").strip()
    if text == BTN_NEW_KEY:
        await newkey(update, context)
    elif text == BTN_STATUS:
        await stats(update, context)
    elif text == BTN_DEVICES:
        await devices(update, context)
    elif text == BTN_KEYS:
        await pending(update, context)
    elif text == BTN_SECURITY:
        await suspicious(update, context)
    elif text == BTN_MENU:
        await menu(update, context)
    elif await _require_role(update):
        await _send_menu(update, "Gunakan tombol menu agar lebih mudah.")


async def flush_outbox(context: ContextTypes.DEFAULT_TYPE) -> None:
    with DATABASE.session_factory() as db:
        admins = db.scalars(select(AdminTelegramUser)).all()
        pending_rows = db.scalars(
            select(NotificationOutbox)
            .where(NotificationOutbox.sent_at.is_(None))
            .order_by(NotificationOutbox.created_at.asc())
            .limit(20)
        ).all()
        for row in pending_rows:
            payload = json.loads(row.payload_json)
            if row.event_type == "device_activated":
                text = (
                    f"✅ Device baru aktif\n{payload['label']}\n"
                    f"Aplikasi: {_app_label(payload['app_type'])}\nWaktu: {payload['activated_at']}"
                )
                markup = None
            elif row.event_type == "session_conflict":
                text = (
                    f"⚠️ Kemungkinan clone\n{payload['label']}\n"
                    f"Aplikasi: {_app_label(payload['app_type'])}\n"
                    f"Percobaan kedua ditolak: {payload['detected_at']}"
                )
                markup = InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        "Abaikan", callback_data=f"suspicion:{payload['suspicion_event_id']}:ignored"
                    ),
                    InlineKeyboardButton(
                        "Revoke Device", callback_data=f"suspicion:{payload['suspicion_event_id']}:revoked"
                    ),
                ]])
            else:
                row.sent_at = utcnow()
                continue
            try:
                for admin in admins:
                    await context.bot.send_message(
                        chat_id=admin.telegram_id,
                        text=text,
                        reply_markup=markup,
                    )
                row.sent_at = utcnow()
                row.last_error = None
            except Exception as exc:  # noqa: BLE001
                row.attempts += 1
                row.last_error = str(exc)[:1000]
                LOGGER.exception("Failed sending notification outbox item %s", row.id)
            db.commit()


async def post_init(application: Application) -> None:
    await application.bot.set_my_commands(
        [
            BotCommand("menu", "Buka menu utama"),
            BotCommand("newkey", "Buat kode aktivasi 1 jam"),
            BotCommand("stats", "Cek status sistem"),
            BotCommand("devices", "Lihat device"),
            BotCommand("pending", "Lihat kode aktif"),
            BotCommand("suspicious", "Lihat peringatan keamanan"),
        ]
    )


def main() -> None:
    SETTINGS.validate()
    with DATABASE.session_factory() as db:
        config = get_or_create_config(db)
        secrets = get_secrets(db, SETTINGS)
        if not config.telegram_enabled or not secrets.telegram_token:
            raise RuntimeError("Telegram bot belum diaktifkan melalui dashboard.")
    logging.basicConfig(
        level=getattr(logging, SETTINGS.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    # Prevent Telegram bot tokens from appearing in HTTP request logs.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("telegram.ext.ExtBot").setLevel(logging.WARNING)

    application = Application.builder().token(secrets.telegram_token).post_init(post_init).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", menu))
    application.add_handler(CommandHandler("newkey", newkey))
    application.add_handler(CommandHandler("devices", devices))
    application.add_handler(CommandHandler("device", device_detail))
    application.add_handler(CommandHandler("pending", pending))
    application.add_handler(CommandHandler("cancelkey", cancelkey))
    application.add_handler(CommandHandler("revoke", revoke))
    application.add_handler(CommandHandler("reactivate", reactivate))
    application.add_handler(CommandHandler("suspicious", suspicious))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CallbackQueryHandler(newkey_callback, pattern=r"^newkey:"))
    application.add_handler(CallbackQueryHandler(cancelkey_callback, pattern=r"^cancelkey:"))
    application.add_handler(CallbackQueryHandler(device_callback, pattern=r"^device:"))
    application.add_handler(CallbackQueryHandler(suspicion_callback, pattern=r"^suspicion:"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, menu_message))
    if application.job_queue is None:
        raise RuntimeError("Install python-telegram-bot[job-queue] to enable outbox processing.")
    application.job_queue.run_repeating(flush_outbox, interval=15, first=5)
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
