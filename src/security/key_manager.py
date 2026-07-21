import os
import stat
from pathlib import Path

from src.security.encryption import generate_key, decrypt_value, encrypt_value


class KeyManager:
    def __init__(self, key_dir: str | Path = "config/keys") -> None:
        self.key_dir = Path(key_dir)
        self._key_file = self.key_dir / ".encryption_key"
        self._ensure_key_dir()

    def _ensure_key_dir(self) -> None:
        self.key_dir.mkdir(parents=True, exist_ok=True)
        if self.key_dir.exists():
            self.key_dir.chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)

    def get_encryption_key(self) -> bytes:
        master_key = os.environ.get("MASTER_KEY")
        if master_key:
            return master_key.encode("utf-8")

        if self._key_file.exists():
            return self._key_file.read_bytes()

        key = generate_key()
        self._key_file.write_bytes(key)
        self._key_file.chmod(stat.S_IRUSR | stat.S_IWUSR)
        return key

    def rotate_key(self) -> None:
        old_key = self.get_encryption_key()
        new_key = generate_key()
        secrets_dir = self.key_dir / "secrets"
        if secrets_dir.exists():
            for secret_file in secrets_dir.iterdir():
                if secret_file.is_file():
                    ciphertext = secret_file.read_text().strip()
                    plaintext = decrypt_value(ciphertext, old_key)
                    new_ciphertext = encrypt_value(plaintext, new_key)
                    secret_file.write_text(new_ciphertext)
        self._key_file.write_bytes(new_key)
        self._key_file.chmod(stat.S_IRUSR | stat.S_IWUSR)
