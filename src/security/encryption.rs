use aes_gcm::{
    aead::{Aead, KeyInit, OsRng},
    Aes256Gcm, Nonce,
};
use anyhow::Result;
use pbkdf2::pbkdf2_hmac;
use rand::RngCore;
use sha2::Sha256;
use std::fs::{self, File};
use std::io::Write;
use std::path::Path;

const KEY_LEN: usize = 32;
const SALT_LEN: usize = 16;
const NONCE_LEN: usize = 12;
const PBKDF2_ITER: u32 = 600_000;

pub struct Crypto {
    key: [u8; KEY_LEN],
}

impl Crypto {
    pub fn new(key_path: &Path) -> Result<Self> {
        let key = if key_path.exists() {
            let data = fs::read(key_path)?;
            let mut key = [0u8; KEY_LEN];
            key.copy_from_slice(&data);
            key
        } else {
            let mut key = [0u8; KEY_LEN];
            OsRng.fill_bytes(&mut key);
            if let Some(parent) = key_path.parent() {
                fs::create_dir_all(parent)?;
            }
            let mut f = File::create(key_path)?;
            #[cfg(unix)]
            {
                use std::os::unix::fs::PermissionsExt;
                f.set_permissions(fs::Permissions::from_mode(0o600))?;
            }
            f.write_all(&key)?;
            key
        };
        Ok(Crypto { key })
    }

    pub fn encrypt(&self, plaintext: &[u8]) -> Result<Vec<u8>> {
        let cipher = Aes256Gcm::new_from_slice(&self.key)?;
        let mut nonce_bytes = [0u8; NONCE_LEN];
        OsRng.fill_bytes(&mut nonce_bytes);
        let nonce = Nonce::from_slice(&nonce_bytes);
        let ct = cipher.encrypt(nonce, plaintext)
            .map_err(|e| anyhow::anyhow!("encryption failed: {e:?}"))?;
        let mut out = nonce_bytes.to_vec();
        out.extend_from_slice(&ct);
        Ok(out)
    }

    pub fn decrypt(&self, data: &[u8]) -> Result<Vec<u8>> {
        if data.len() < NONCE_LEN {
            anyhow::bail!("ciphertext too short");
        }
        let (nonce_bytes, ct) = data.split_at(NONCE_LEN);
        let cipher = Aes256Gcm::new_from_slice(&self.key)?;
        let nonce = Nonce::from_slice(nonce_bytes);
        let pt = cipher.decrypt(nonce, ct)
            .map_err(|e| anyhow::anyhow!("decryption failed: {e:?}"))?;
        Ok(pt)
    }

    pub fn hash_password(password: &str, salt: &[u8]) -> [u8; KEY_LEN] {
        let mut hash = [0u8; KEY_LEN];
        pbkdf2_hmac::<Sha256>(password.as_bytes(), salt, PBKDF2_ITER, &mut hash);
        hash
    }

    pub fn generate_salt() -> [u8; SALT_LEN] {
        let mut salt = [0u8; SALT_LEN];
        OsRng.fill_bytes(&mut salt);
        salt
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    #[test]
    fn test_encrypt_decrypt_roundtrip() {
        let dir = TempDir::new().unwrap();
        let path = dir.path().join("test.key");
        let crypto = Crypto::new(&path).unwrap();
        let plaintext = b"Hello, Bloomberg Terminal!";
        let ciphertext = crypto.encrypt(plaintext).unwrap();
        let decrypted = crypto.decrypt(&ciphertext).unwrap();
        assert_eq!(plaintext.to_vec(), decrypted);
    }

    #[test]
    fn test_encrypt_empty_data() {
        let dir = TempDir::new().unwrap();
        let path = dir.path().join("test.key");
        let crypto = Crypto::new(&path).unwrap();
        let ciphertext = crypto.encrypt(b"").unwrap();
        let decrypted = crypto.decrypt(&ciphertext).unwrap();
        assert!(decrypted.is_empty());
    }

    #[test]
    fn test_decrypt_tampered_ciphertext_fails() {
        let dir = TempDir::new().unwrap();
        let path = dir.path().join("test.key");
        let crypto = Crypto::new(&path).unwrap();
        let plaintext = b"sensitive data";
        let mut ciphertext = crypto.encrypt(plaintext).unwrap();
        ciphertext[15] ^= 0xFF;
        assert!(crypto.decrypt(&ciphertext).is_err());
    }

    #[test]
    fn test_decrypt_too_short_fails() {
        let dir = TempDir::new().unwrap();
        let path = dir.path().join("test.key");
        let crypto = Crypto::new(&path).unwrap();
        let result = crypto.decrypt(b"too_short");
        assert!(result.is_err());
    }

    #[test]
    fn test_password_hash_deterministic() {
        let salt = Crypto::generate_salt();
        let hash1 = Crypto::hash_password("my_password", &salt);
        let hash2 = Crypto::hash_password("my_password", &salt);
        assert_eq!(hash1, hash2);
    }

    #[test]
    fn test_password_hash_different_salts() {
        let salt1 = Crypto::generate_salt();
        let salt2 = Crypto::generate_salt();
        let hash1 = Crypto::hash_password("same_password", &salt1);
        let hash2 = Crypto::hash_password("same_password", &salt2);
        assert_ne!(hash1, hash2);
    }

    #[test]
    fn test_password_hash_different_inputs() {
        let salt = Crypto::generate_salt();
        let hash1 = Crypto::hash_password("password1", &salt);
        let hash2 = Crypto::hash_password("password2", &salt);
        assert_ne!(hash1, hash2);
    }

    #[test]
    fn test_salt_length() {
        let salt = Crypto::generate_salt();
        assert_eq!(salt.len(), 16);
    }

    #[test]
    fn test_key_file_created_with_600_perms() {
        let dir = TempDir::new().unwrap();
        let path = dir.path().join("test.key");
        let _crypto = Crypto::new(&path).unwrap();
        assert!(path.exists());
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            let meta = std::fs::metadata(&path).unwrap();
            let perms = meta.permissions();
            assert_eq!(perms.mode() & 0o777, 0o600);
        }
    }

    #[test]
    fn test_key_reused_across_sessions() {
        let dir = TempDir::new().unwrap();
        let path = dir.path().join("persistent.key");
        let crypto1 = Crypto::new(&path).unwrap();
        let crypto2 = Crypto::new(&path).unwrap();
        let ct = crypto1.encrypt(b"persistent").unwrap();
        let pt = crypto2.decrypt(&ct).unwrap();
        assert_eq!(&pt, b"persistent");
    }

    #[test]
    fn test_encrypt_large_data() {
        let dir = TempDir::new().unwrap();
        let path = dir.path().join("test.key");
        let crypto = Crypto::new(&path).unwrap();
        let large = vec![0xABu8; 65_536];
        let ct = crypto.encrypt(&large).unwrap();
        let pt = crypto.decrypt(&ct).unwrap();
        assert_eq!(large, pt);
    }

    #[test]
    fn test_multiple_encrypts_different_nonces() {
        let dir = TempDir::new().unwrap();
        let path = dir.path().join("test.key");
        let crypto = Crypto::new(&path).unwrap();
        let data = b"same data";
        let ct1 = crypto.encrypt(data).unwrap();
        let ct2 = crypto.encrypt(data).unwrap();
        assert_ne!(ct1, ct2, "nonce reuse would break security");
    }
}
