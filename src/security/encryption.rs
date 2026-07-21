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
