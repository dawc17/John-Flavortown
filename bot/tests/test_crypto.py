from bot.crypto import encrypt_api_key, decrypt_api_key

def test_encrypt_decrypt_roundtrip():
    api_key = "abc123"
    password = "correcthorsebatterystaple!!!"

    encrypted, salt = encrypt_api_key(api_key, password)
    assert encrypted != api_key
    assert salt

    decrypted = decrypt_api_key(encrypted, salt, password)
    assert decrypted == api_key

def test_decrypt_wrong_password_none():
    api_key = "abc123"
    encrypted, salt = encrypt_api_key(api_key, "rightpassword")

    decrypted = decrypt_api_key(encrypted, salt, "wrongpasswordbruh")
    assert decrypted is None