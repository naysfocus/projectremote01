from __future__ import annotations

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def test_upgrade_from_v12_schema_to_v15(tmp_path, monkeypatch):
    database_url = f"sqlite:///{tmp_path / 'migration.db'}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)

    command.upgrade(config, "0001")
    engine = create_engine(database_url)
    assert "session_version" not in {column["name"] for column in inspect(engine).get_columns("admin_users")}
    engine.dispose()

    command.upgrade(config, "head")
    engine = create_engine(database_url)
    assert "session_version" in {column["name"] for column in inspect(engine).get_columns("admin_users")}
    integration_columns = {column["name"] for column in inspect(engine).get_columns("integration_config")}
    assert {"telegram_token_encrypted", "cloudflare_token_encrypted", "public_base_url", "cloudflare_protocol"}.issubset(integration_columns)
    with engine.connect() as connection:
        assert connection.exec_driver_sql("SELECT version_num FROM alembic_version").scalar_one() == "0007"
    engine.dispose()


def test_upgrade_from_v131_keeps_existing_admin_and_data(tmp_path, monkeypatch):
    database_url = f"sqlite:///{tmp_path / 'upgrade-v131.db'}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)

    command.upgrade(config, "0002")
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "INSERT INTO admin_users "
            "(username,password_hash,is_active,created_at,session_version) "
            "VALUES ('existing-admin','hash',1,CURRENT_TIMESTAMP,3)"
        )
    engine.dispose()

    command.upgrade(config, "head")
    engine = create_engine(database_url)
    with engine.connect() as connection:
        assert connection.exec_driver_sql(
            "SELECT username FROM admin_users WHERE username='existing-admin'"
        ).scalar_one() == "existing-admin"
        assert connection.exec_driver_sql("SELECT version_num FROM alembic_version").scalar_one() == "0007"
    assert "integration_config" in inspect(engine).get_table_names()
    engine.dispose()


def test_upgrade_from_v14_preserves_integration_settings(tmp_path, monkeypatch):
    database_url = f"sqlite:///{tmp_path / 'upgrade-v14.db'}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)

    command.upgrade(config, "0003")
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "INSERT INTO integration_config "
            "(id,telegram_enabled,cloudflare_enabled,public_base_url,revision,updated_at) "
            "VALUES (1,1,1,'https://scaleup.example.com',7,CURRENT_TIMESTAMP)"
        )
    engine.dispose()

    command.upgrade(config, "head")
    engine = create_engine(database_url)
    with engine.connect() as connection:
        row = connection.exec_driver_sql(
            "SELECT public_base_url,revision,cloudflare_protocol FROM integration_config WHERE id=1"
        ).one()
        assert row.public_base_url == "https://scaleup.example.com"
        assert row.revision == 7
        assert row.cloudflare_protocol == "auto"
        assert connection.exec_driver_sql("SELECT version_num FROM alembic_version").scalar_one() == "0007"
    engine.dispose()


def test_upgrade_0004_to_0005_preserves_device_children(tmp_path, monkeypatch):
    database_url = f"sqlite:///{tmp_path / 'upgrade-preserve.db'}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "0004")
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "INSERT INTO devices (fingerprint_hash,label,os_type,first_seen_at) "
            "VALUES ('" + "f" * 64 + "','Device Lama','windows',CURRENT_TIMESTAMP)"
        )
        device_id = connection.exec_driver_sql("SELECT id FROM devices").scalar_one()
        connection.exec_driver_sql(
            "INSERT INTO activity_reports "
            "(device_id,app_type,event_type,occurred_at,received_at,summary_json,client_report_id) "
            "VALUES (?, 'matrix_generator','generate_completed',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP,?, 'old-report')",
            (device_id, '{"mode":"classic","video_count":30000,"duration_seconds":100,"run_tag":"old"}'),
        )
    engine.dispose()
    command.upgrade(config, "head")
    engine = create_engine(database_url)
    with engine.connect() as connection:
        assert connection.exec_driver_sql("SELECT count(*) FROM devices").scalar_one() == 1
        assert connection.exec_driver_sql("SELECT count(*) FROM activity_reports").scalar_one() == 1
        assert connection.exec_driver_sql("SELECT version_num FROM alembic_version").scalar_one() == "0007"
    engine.dispose()


def test_upgrade_0005_to_0006_preserves_existing_v16_data(tmp_path, monkeypatch):
    database_url = f"sqlite:///{tmp_path / 'upgrade-v16-to-v161.db'}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "0005")
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "INSERT INTO devices (fingerprint_hash,label,os_type,first_seen_at) VALUES (?, 'Remote HP Lama','windows',CURRENT_TIMESTAMP)",
            ("9" * 64,),
        )
        device_id = connection.exec_driver_sql("SELECT id FROM devices").scalar_one()
        connection.exec_driver_sql(
            "INSERT INTO activity_reports (device_id,app_type,event_type,occurred_at,received_at,summary_json,client_report_id) "
            "VALUES (?, 'remote_hp','upload_session_completed',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP,?, 'legacy-upload')",
            (device_id, '{"local_session_id":1,"account_username":"akun-lama","video_count":24,"batch_date":"2026-08-05","status":"finished"}'),
        )
    engine.dispose()
    command.upgrade(config, "head")
    engine = create_engine(database_url)
    with engine.connect() as connection:
        assert connection.exec_driver_sql("SELECT count(*) FROM devices").scalar_one() == 1
        assert connection.exec_driver_sql("SELECT count(*) FROM activity_reports").scalar_one() == 1
        tables = set(inspect(engine).get_table_names())
        assert {"remote_hp_handsets", "remote_hp_accounts", "remote_hp_placements", "remote_hp_upload_sessions"}.issubset(tables)
        assert connection.exec_driver_sql("SELECT version_num FROM alembic_version").scalar_one() == "0007"
    engine.dispose()


def test_upgrade_0006_to_0007_preserves_remote_hp_inventory_and_sessions(tmp_path, monkeypatch):
    database_url = f"sqlite:///{tmp_path / 'upgrade-v17.db'}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "0006")
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "INSERT INTO devices (fingerprint_hash,label,os_type,first_seen_at) VALUES (?, 'Remote HP Produksi','windows',CURRENT_TIMESTAMP)",
            ("7" * 64,),
        )
        device_id = connection.exec_driver_sql("SELECT id FROM devices").scalar_one()
        connection.exec_driver_sql(
            "INSERT INTO remote_hp_handsets (server_device_id,client_device_id,name,serial,is_present,is_online,last_synced_at) VALUES (?,1,'HP Lama','USB-OLD',1,1,CURRENT_TIMESTAMP)",
            (device_id,),
        )
        handset_id = connection.exec_driver_sql("SELECT id FROM remote_hp_handsets").scalar_one()
        connection.exec_driver_sql(
            "INSERT INTO remote_hp_accounts (server_device_id,client_account_id,username,is_present,last_synced_at) VALUES (?,10,'akun.lama',1,CURRENT_TIMESTAMP)",
            (device_id,),
        )
        account_id = connection.exec_driver_sql("SELECT id FROM remote_hp_accounts").scalar_one()
        connection.exec_driver_sql(
            "INSERT INTO remote_hp_upload_sessions (server_device_id,client_session_id,account_id,handset_id,status,planned_count,completed_count,failed_count,is_present,last_synced_at) VALUES (?,501,?,?, 'finished',24,24,0,1,CURRENT_TIMESTAMP)",
            (device_id, account_id, handset_id),
        )
    engine.dispose()

    command.upgrade(config, "head")
    engine = create_engine(database_url)
    columns = {column["name"] for column in inspect(engine).get_columns("remote_hp_handsets")}
    assert {"stable_uid", "usb_serial", "wifi_endpoint", "preferred_transport", "active_transport", "active_serial"}.issubset(columns)
    assert "remote_hp_mobile_clients" in inspect(engine).get_table_names()
    with engine.connect() as connection:
        assert connection.exec_driver_sql("SELECT count(*) FROM remote_hp_handsets").scalar_one() == 1
        assert connection.exec_driver_sql("SELECT count(*) FROM remote_hp_upload_sessions").scalar_one() == 1
        assert connection.exec_driver_sql("SELECT version_num FROM alembic_version").scalar_one() == "0007"
    engine.dispose()
