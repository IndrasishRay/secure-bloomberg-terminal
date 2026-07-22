use bloomberg_terminal::security::encryption::Crypto;
use bloomberg_terminal::db::Database;
use tempfile::TempDir;

#[test]
fn test_encrypt_decrypt_small_data() {
    let dir = TempDir::new().unwrap();
    let path = dir.path().join("key");
    let crypto = Crypto::new(&path).unwrap();
    let plaintext = b"Hello, world!";
    let ct = crypto.encrypt(plaintext).unwrap();
    let pt = crypto.decrypt(&ct).unwrap();
    assert_eq!(pt, plaintext);
}

#[test]
fn test_encrypt_decrypt_empty() {
    let dir = TempDir::new().unwrap();
    let path = dir.path().join("key");
    let crypto = Crypto::new(&path).unwrap();
    let ct = crypto.encrypt(b"").unwrap();
    let pt = crypto.decrypt(&ct).unwrap();
    assert!(pt.is_empty());
}

#[test]
fn test_encrypt_decrypt_large() {
    let dir = TempDir::new().unwrap();
    let path = dir.path().join("key");
    let crypto = Crypto::new(&path).unwrap();
    let data = vec![0x42u8; 131_072];
    let ct = crypto.encrypt(&data).unwrap();
    let pt = crypto.decrypt(&ct).unwrap();
    assert_eq!(pt, data);
}

#[test]
fn test_tampered_ciphertext_rejected() {
    let dir = TempDir::new().unwrap();
    let path = dir.path().join("key");
    let crypto = Crypto::new(&path).unwrap();
    let mut ct = crypto.encrypt(b"important").unwrap();
    ct[20] ^= 0xFF;
    assert!(crypto.decrypt(&ct).is_err());
}

#[test]
fn test_truncated_ciphertext_rejected() {
    let dir = TempDir::new().unwrap();
    let path = dir.path().join("key");
    let crypto = Crypto::new(&path).unwrap();
    assert!(crypto.decrypt(b"too_short").is_err());
}

#[test]
fn test_key_reuse_across_sessions() {
    let dir = TempDir::new().unwrap();
    let path = dir.path().join("shared.key");
    let c1 = Crypto::new(&path).unwrap();
    let ct = c1.encrypt(b"persistent secret").unwrap();
    let c2 = Crypto::new(&path).unwrap();
    let pt = c2.decrypt(&ct).unwrap();
    assert_eq!(pt, b"persistent secret");
}

#[test]
fn test_salt_generation_length() {
    let salt = Crypto::generate_salt();
    assert_eq!(salt.len(), 16);
}

#[test]
fn test_salt_uniqueness() {
    let s1 = Crypto::generate_salt();
    let s2 = Crypto::generate_salt();
    assert_ne!(s1, s2);
}

#[test]
fn test_password_hash_deterministic() {
    let salt = Crypto::generate_salt();
    let h1 = Crypto::hash_password("mypassword", &salt);
    let h2 = Crypto::hash_password("mypassword", &salt);
    assert_eq!(h1, h2);
}

#[test]
fn test_password_hash_different_salts() {
    let s1 = Crypto::generate_salt();
    let s2 = Crypto::generate_salt();
    let h1 = Crypto::hash_password("same", &s1);
    let h2 = Crypto::hash_password("same", &s2);
    assert_ne!(h1, h2);
}

#[test]
fn test_password_hash_empty() {
    let salt = Crypto::generate_salt();
    let h = Crypto::hash_password("", &salt);
    assert_eq!(h.len(), 32);
}

#[test]
fn test_password_hash_long_input() {
    let salt = Crypto::generate_salt();
    let long = "a".repeat(1000);
    let h = Crypto::hash_password(&long, &salt);
    assert_eq!(h.len(), 32);
}

#[test]
fn test_audit_log_in_db() {
    let dir = TempDir::new().unwrap();
    let db = Database::new(&dir.path().join("audit.db")).unwrap();
    db.log_audit("LOGIN", "test_user", "test login", "10.0.0.1").unwrap();
    let logs = db.get_audit_logs(10);
    assert_eq!(logs.len(), 1);
    assert_eq!(logs[0].action, "LOGIN");
    assert_eq!(logs[0].user, "test_user");
    assert_eq!(logs[0].ip_address, "10.0.0.1");
}

#[test]
fn test_audit_log_multiple_entries() {
    let dir = TempDir::new().unwrap();
    let db = Database::new(&dir.path().join("audit.db")).unwrap();
    for i in 0..5 {
        db.log_audit(&format!("ACTION_{}", i), "user", "details", "127.0.0.1").unwrap();
    }
    let logs = db.get_audit_logs(10);
    assert_eq!(logs.len(), 5);
}

#[test]
fn test_audit_log_persists_only_logged_events() {
    let dir = TempDir::new().unwrap();
    let db = Database::new(&dir.path().join("audit.db")).unwrap();
    let logs = db.get_audit_logs(10);
    assert!(logs.is_empty());
}
