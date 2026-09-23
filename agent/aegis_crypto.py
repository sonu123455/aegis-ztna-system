import os
import hashlib
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

class AegisVault:
    def __init__(self, key_file="aegis_master.key"):
        self.key_file = key_file
        self.key = self._load_or_generate_key()
        self.aesgcm = AESGCM(self.key)

    def _load_or_generate_key(self) -> bytes:
        if os.path.exists(self.key_file):
            with open(self.key_file, "rb") as f:
                return f.read()
        else:
            key = AESGCM.generate_key(bit_length=256)
            with open(self.key_file, "wb") as f:
                f.write(key)
            return key

    def _hash_passphrase(self, passphrase: str, salt: bytes) -> bytes:
        """Derives a salted cryptographic hash of the secret passphrase."""
        return hashlib.sha256(salt + passphrase.encode("utf-8")).digest()

    def encrypt_file(self, target_filepath: str, secret_passphrase: str) -> str:
        """
        Encrypts a file and prepends authentication metadata:
        [16-byte Salt] + [32-byte Passphrase Hash] + [12-byte Nonce] + [Ciphertext + GCM Tag]
        """
        if not os.path.exists(target_filepath):
            raise FileNotFoundError(f"File not found: {target_filepath}")

        with open(target_filepath, "rb") as f:
            plaintext = f.read()

        salt = os.urandom(16)
        passphrase_hash = self._hash_passphrase(secret_passphrase, salt)
        nonce = os.urandom(12)
        ciphertext = self.aesgcm.encrypt(nonce, plaintext, None)

        locked_filepath = target_filepath + ".aegis"
        with open(locked_filepath, "wb") as f:
            f.write(salt + passphrase_hash + nonce + ciphertext)

        os.remove(target_filepath)
        return locked_filepath

    def verify_passphrase(self, locked_filepath: str, candidate_passphrase: str) -> bool:
        """Checks if the candidate passphrase string matches the encrypted asset's registered hash."""
        if not os.path.exists(locked_filepath):
            return False

        with open(locked_filepath, "rb") as f:
            header = f.read(48)  # 16 bytes salt + 32 bytes hash

        if len(header) < 48:
            return False

        salt = header[:16]
        expected_hash = header[16:48]
        computed_hash = self._hash_passphrase(candidate_passphrase, salt)
        return computed_hash == expected_hash

    def decrypt_file(self, locked_filepath: str) -> str:
        """Decrypts a .aegis file back to its original cleartext format."""
        if not locked_filepath.endswith(".aegis") or not os.path.exists(locked_filepath):
            raise ValueError("Target file is not a valid .aegis asset.")

        with open(locked_filepath, "rb") as f:
            payload = f.read()

        # Skip header: 16 bytes salt + 32 bytes hash = 48 bytes offset
        nonce = payload[48:60]
        ciphertext = payload[60:]

        decrypted_data = self.aesgcm.decrypt(nonce, ciphertext, None)

        original_filepath = locked_filepath[:-6]
        with open(original_filepath, "wb") as f:
            f.write(decrypted_data)

        os.remove(locked_filepath)
        return original_filepath
