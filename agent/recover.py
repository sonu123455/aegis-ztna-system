import sys
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

def recover_file(file_path, passphrase):
    print(f"[*] Reading encrypted file: {file_path}")
    with open(file_path, "rb") as f:
        data = f.read()

    # Extract WebCrypto Envelope: 16-byte Salt + 12-byte IV + Ciphertext
    salt = data[:16]
    iv = data[16:28]
    ciphertext = data[28:]

    print(f"[*] Deriving 256-bit AES key via PBKDF2 (100,000 rounds)...")
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000
    )
    key = kdf.derive(passphrase.strip().encode('utf-8'))
    aesgcm = AESGCM(key)

    try:
        decrypted_bytes = aesgcm.decrypt(iv, ciphertext, None)
        with open(file_path, "wb") as f:
            f.write(decrypted_bytes)
        print(f"\n[✓] SUCCESS: '{file_path}' has been restored to its original cleartext!")
    except Exception as e:
        print(f"\n[!] Decryption failed. Ensure the passphrase is correct: {e}")

if __name__ == "__main__":
    target = input("Enter path of locked file: ").strip().strip('"')
    secret = input("Enter passphrase used when locking: ").strip()
    recover_file(target, secret)
