import os
import requests

# Exact match to your phone topic
NTFY_TOPIC = "aegis_alerts"

def send_phone_push_notification(user_principal: str, target_resource: str, risk_score: float, cadence_ms: float, tx_hash: str):
    """Dispatches instant push notification directly to phone via ntfy.sh."""
    try:
        payload = {
            "topic": NTFY_TOPIC,
            "title": "🚨 Aegis ZTNA: Access Denied",
            "message": (
                f"STOLEN CREDENTIAL ALERT!\n"
                f"Principal: {user_principal}\n"
                f"Target: {target_resource}\n"
                f"Cadence: {cadence_ms} ms (Anomalous)\n"
                f"Risk Score: {risk_score}%\n"
                f"Policy: Asset Locked on Disk"
            ),
            "priority": 5,
            "tags": ["warning", "shield", "lock"]
        }
        res = requests.post("https://ntfy.sh", json=payload, timeout=4.0)
        print(f"[+] Phone alert dispatched to topic '{NTFY_TOPIC}', status: {res.status_code}")
    except Exception as e:
        print(f"[!] Alert dispatch error: {e}")

def dispatch_security_alerts(user_principal: str, target_resource: str, risk_score: float, cadence_ms: float, tx_hash: str):
    send_phone_push_notification(user_principal, target_resource, risk_score, cadence_ms, tx_hash)
