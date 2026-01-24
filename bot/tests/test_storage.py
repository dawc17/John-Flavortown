import importlib

import bot.storage as storage

def _use_temp_db(tmp_path):
    # temp db for test run
    storage.DATA_DIR = tmp_path
    storage.DB_PATH = tmp_path / "bruh.db"
    storage._db_initialized = False
    storage.init_db()

def test_store_get_delete_flow(tmp_path):
    _use_temp_db(tmp_path)

    discord_id = 123
    service = "flavortown"
    encrypted = "enc"
    salt = "salt"
    metadata = '{"foo":"bar"}'

    # store
    storage.store_encrypted_key(discord_id, service, encrypted, salt, metadata)

    # get
    result = storage.get_encrypted_key(discord_id, service)
    assert result == (encrypted, salt, metadata)

    # has key
    assert storage.user_has_key(discord_id, service) is True

    # delete
    deleted = storage.delete_user_key(discord_id, service)
    assert deleted is True
    assert storage.get_encrypted_key(discord_id, service) is None
    assert storage.user_has_key(discord_id, service) is False

def test_delete_all(tmp_path):
    _use_temp_db(tmp_path)

    discord_id = 555

    storage.store_encrypted_key(discord_id, "flavortown", "e1", "s1", None)
    storage.store_encrypted_key(discord_id, "hackatime", "e2", "s2", None)

    deleted = storage.delete_user_key(discord_id)
    assert deleted is True
    assert storage.get_encrypted_key(discord_id, "flavortown") is None
    assert storage.get_encrypted_key(discord_id, "hackatime") is None