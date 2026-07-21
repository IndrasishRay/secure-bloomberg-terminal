import base64
import os
from pathlib import Path

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


def generate_key() -> bytes:
    return Fernet.generate_key()


def encrypt_value(plaintext: str, key: bytes) -> str:
    f = Fernet(key)
    token = f.encrypt(plaintext.encode("utf-8"))
    return base64.urlsafe_b64encode(token).decode("utf-8")


def decrypt_value(ciphertext: str, key: bytes) -> str:
    f = Fernet(key)
    token = base64.urlsafe_b64decode(ciphertext.encode("utf-8"))
    return f.decrypt(token).decode("utf-8")


def encrypt_file(filepath: Path, key: bytes) -> None:
    f = Fernet(key)
    data = filepath.read_bytes()
    encrypted = f.encrypt(data)
    filepath.write_bytes(encrypted)


def decrypt_file(filepath: Path, key: bytes) -> None:
    f = Fernet(key)
    data = filepath.read_bytes()
    decrypted = f.decrypt(data)
    filepath.write_bytes(decrypted)


def derive_key_from_password(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=600_000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(password.encode("utf-8")))
    return key
