import os
import sys
import time
import socket
import getpass
import requests
from datetime import datetime
from aegis_crypto import AegisVault

try:
    import msvcrt
except ImportError:
    msvcrt = None

GATEWAY_URL = "https://aegis-ztna-system.onrender.com/api/v1/evaluate-risk"
violation_counter = 0


def capture_keystroke_cadence(prompt="Enter Passphrase: ") -> tuple[str, float]:
    """Captures input and measures Inter-Key Timing (IKT) in milliseconds."""
    print(prompt, end="", flush=True)
    chars = []
    intervals_ms = []
    last_time = None

    if msvcrt:
        while True:
            ch = msvcrt.getwch()
            now = time.perf_counter()

            if ch in ("\r", "\n"):
                print()
                break
            elif ch == "\x08":  # Backspace
                if chars:
                    chars.pop()
                    print("\b \b", end="", flush=True)
            else:
                chars.append(ch)
                print("*", end="", flush=True)
                if last_time is not None:
                    intervals_ms.append((now - last_time) * 1000.0)
                last_time = now
    else:
        start = time.perf_counter()
        entered = getpass.getpass(prompt="")
        total_ms = (time.perf_counter() - start) * 1000.0
        cadence = total_ms / max(len(entered), 1)
        return entered, round(cadence, 2)

    entered_text = "".join(chars)
    avg_cadence = sum(intervals_ms) / len(intervals_ms) if intervals_ms else 180.0
    return entered_text, round(avg_cadence, 2)


def get_system_posture() -> dict:
    hostname = socket.gethostname()
    try:
        ip = socket.gethostbyname(hostname)
    except Exception:
        ip = "127.0.0.1"

    return {
        "user_principal": f"{getpass.getuser()}@{hostname}",
        "host_ip": ip,
        "access_hour": datetime.now().hour,
        "os_platform": sys.platform
    }


def verify_with_policy_engine(telemetry: dict) -> tuple[str, float, str]:
    try:
        resp = requests.post(GATEWAY_URL, json=telemetry, timeout=4.0)
        if resp.status_code in (200, 403):
            data = resp.json()
            return data.get("decision", "DENIED"), data.get("risk_score_percent", 99.0), data.get("tx_hash", "0xPending")
    except Exception:
        cadence = telemetry["keystroke_cadence"]
        if 110.0 <= cadence <= 340.0:
            return "GRANTED", round(abs(cadence - 210.0) * 0.15 + 12.0, 2), "0xLocalFallbackProof"
        return "DENIED", round(min(abs(cadence - 210.0) * 0.35 + 55.0, 97.5), 2), "0xLocalFallbackProof"


def main():
    global violation_counter
    vault = AegisVault()
    print("\n=======================================================")
    print("      AEGIS ZERO TRUST - ENDPOINT SECURITY AGENT      ")
    print("=======================================================")
    print("1. Lock File (Set Secret Passphrase & Encrypt)")
    print("2. Biometric Unlock Challenge")
    print("3. Exit")

    choice = input("\nSelect Action [1/2/3]: ").strip()

    if choice == "1":
        file_name = input("Enter filename to lock (e.g., test.txt): ").strip()
        if not os.path.exists(file_name):
            print(f"[!] File '{file_name}' not found.")
            return

        passphrase_1 = getpass.getpass("Set Secret Passphrase for this asset: ")
        passphrase_2 = getpass.getpass("Confirm Secret Passphrase: ")

        if passphrase_1 != passphrase_2 or not passphrase_1:
            print("[!] Error: Passphrases do not match or empty.")
            return

        locked_path = vault.encrypt_file(file_name, passphrase_1)
        print(f"\n[+] ASSET LOCKED: Generated vault -> {locked_path}")
        print("[+] Salted SHA-256 hash & AES-256-GCM envelope committed to file header.")

    elif choice == "2":
        locked_file = input("Enter .aegis file to unlock: ").strip()
        if not os.path.exists(locked_file):
            print(f"[!] File '{locked_file}' not found.")
            return

        posture = get_system_posture()
        print("\n[AEGIS BIOMETRIC CHALLENGE INITIALIZED]")
        passphrase, cadence_ms = capture_keystroke_cadence("Enter Security Passphrase: ")

        # ----------------- TIER 1: CREDENTIAL STRING VERIFICATION -----------------
        is_passphrase_correct = vault.verify_passphrase(locked_file, passphrase)
        if not is_passphrase_correct:
            violation_counter += 1
            print("\n[🚨] AUTHENTICATION FAILED: Incorrect Passphrase String!")
            print(f"[!] Security violation counter incremented: {violation_counter}")
            print("[🔒] Access blocked immediately. File remains encrypted.")
            return

        print("\n[✓] Tier 1 Passed: Passphrase string is VALID.")
        print("[*] Tier 2 Initiated: Evaluating Zero Trust behavioral biometrics with Cloud AI...")

        # ------------- TIER 2: ZERO TRUST BEHAVIORAL AI INFERENCE -------------
        telemetry = {
            "user_principal": posture["user_principal"],
            "target_resource": os.path.basename(locked_file),
            "access_hour": posture["access_hour"],
            "keystroke_cadence": cadence_ms,
            "violation_count": violation_counter
        }

        decision, risk_score, tx_hash = verify_with_policy_engine(telemetry)

        print("\n---------------- POLICY DECISION ----------------")
        print(f"  Biometric Cadence (IKT) : {cadence_ms} ms")
        print(f"  Calculated Risk Score   : {risk_score}%")
        print(f"  Enforcement Decision    : {decision}")
        print(f"  Blockchain Audit Hash   : {tx_hash}")
        print("-------------------------------------------------")

        if decision == "GRANTED":
            print("\n[✓] ZTNA PERIMETER CLEAR: Decrypting asset into memory...")
            unlocked_path = vault.decrypt_file(locked_file)
            print(f"[✓] SUCCESS: File restored to -> {unlocked_path}")
            os.system(f'start "" "{unlocked_path}"')
        else:
            print("\n[🚨] ZERO TRUST INTERCEPTION: Passphrase was CORRECT, but BEHAVIOR IS ANOMALOUS!")
            print("[🔒] Imposter typing rhythm detected. Asset remains AES-256 locked on disk.")

    elif choice == "3":
        sys.exit(0)


if __name__ == "__main__":
    main()
