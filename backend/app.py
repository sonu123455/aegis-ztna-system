import os
import time
import joblib
import numpy as np
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from threading import Thread

# Local module imports
from alerts import dispatch_security_alerts
from train_model import train_and_export
from blockchain import blockchain_logger

app = FastAPI(
    title="Aegis ZTNA Policy Controller",
    description="Decentralized Zero Trust AI Gateway & Policy Decision Point",
    version="1.0.0"
)

# Enable CORS for local endpoint agent testing and cloud React frontend deployments
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "ztna_model.joblib")

# Resilient model loader: auto-trains baseline if model is missing, empty, or incompatible
model = None
if os.path.exists(MODEL_PATH) and os.path.getsize(MODEL_PATH) > 100:
    try:
        model = joblib.load(MODEL_PATH)
        print(f"[+] Loaded Isolation Forest model from: {MODEL_PATH}")
    except Exception as err:
        print(f"[!] Error unpickling {MODEL_PATH} ({err}). Rebuilding baseline model...")
        model = None

if model is None:
    print("[*] Training and serializing fresh Isolation Forest baseline model...")
    model = train_and_export(MODEL_PATH)

# In-memory circular buffer for dashboard telemetry streaming
telemetry_audit_store = []


class TelemetryPayload(BaseModel):
    user_principal: str = Field(..., example="Anoop@LAPTOP-J46QBDUG")
    target_resource: str = Field(..., example="ML Expt 6.pdf.aegis")
    access_hour: int = Field(..., ge=0, le=23, example=22)
    keystroke_cadence: float = Field(..., ge=5.0, le=3000.0, example=204.41)
    violation_count: int = Field(default=0, ge=0, example=0)


class PolicyDecisionResponse(BaseModel):
    decision: str
    risk_score_percent: float
    is_anomaly: bool
    status_code: int
    session_token: str | None
    timestamp: str
    audit_id: str
    tx_hash: str
    block_number: int
    explorer_url: str


@app.get("/")
def health_check():
    return {
        "system": "Aegis ZTNA Policy Controller",
        "status": "ONLINE",
        "model_loaded": model is not None,
        "policy_rule": "Risk Score < 60.0% => GRANTED"
    }


@app.post("/api/v1/evaluate-risk", response_model=PolicyDecisionResponse)
def evaluate_access_risk(payload: TelemetryPayload):
    global model
    if model is None:
        if os.path.exists(MODEL_PATH) and os.path.getsize(MODEL_PATH) > 100:
            try:
                model = joblib.load(MODEL_PATH)
            except Exception:
                model = train_and_export(MODEL_PATH)
        else:
            model = train_and_export(MODEL_PATH)

    # Multi-vector feature vector: [cadence, access_hour, violation_count]
    features = np.array([[
        payload.keystroke_cadence,
        float(payload.access_hour),
        float(payload.violation_count)
    ]])

    # Isolation Forest: 1 = Normal (Inlier), -1 = Anomaly (Outlier)
    prediction = model.predict(features)[0]
    raw_decision_score = model.decision_function(features)[0]

    # Normalize raw score to a risk percentage (0.0% - 100.0%)
    calculated_risk = (0.28 - raw_decision_score) * 125.0
    risk_percent = round(float(np.clip(calculated_risk, 4.0, 98.5)), 2)

    # Zero Trust Policy threshold: Deny access if predicted outlier or risk >= 60.0%
    is_anomaly = True if (prediction == -1 or risk_percent >= 60.0) else False
    decision = "DENIED" if is_anomaly else "GRANTED"
    session_token = f"AEGIS-SESSION-{int(time.time())}-PASS" if not is_anomaly else None

    audit_id = f"ZT-{int(time.time() * 1000)}"

    # Commit the immutable audit record to the Web3 ledger
    chain_receipt = blockchain_logger.commit_audit_record(
        audit_id=audit_id,
        user_principal=payload.user_principal,
        target_resource=payload.target_resource,
        risk_score=risk_percent,
        decision=decision
    )

    # Trigger real-time Phone/Email alerts on anomalous denial (Stolen password simulation)
    if decision == "DENIED":
        try:
            Thread(
                target=dispatch_security_alerts,
                args=(
                    payload.user_principal,
                    payload.target_resource,
                    risk_percent,
                    payload.keystroke_cadence,
                    chain_receipt.get("tx_hash", "0xPending")
                ),
                daemon=True
            ).start()
        except Exception as alert_err:
            print(f"[!] Alert dispatch error: {alert_err}")

    # Ingest event into the active SOC telemetry feed
    event_entry = {
        "audit_id": audit_id,
        "user_principal": payload.user_principal,
        "target_resource": payload.target_resource,
        "cadence_ms": payload.keystroke_cadence,
        "access_hour": payload.access_hour,
        "risk_score_percent": risk_percent,
        "decision": decision,
        "tx_hash": chain_receipt["tx_hash"],
        "block_number": chain_receipt["block_number"],
        "explorer_url": chain_receipt["explorer_url"],
        "timestamp": chain_receipt["committed_at"]
    }
    telemetry_audit_store.insert(0, event_entry)

    # Maintain maximum 50 recent records in memory
    if len(telemetry_audit_store) > 50:
        telemetry_audit_store.pop()

    return PolicyDecisionResponse(
        decision=decision,
        risk_score_percent=risk_percent,
        is_anomaly=is_anomaly,
        status_code=200 if not is_anomaly else 403,
        session_token=session_token,
        timestamp=event_entry["timestamp"],
        audit_id=audit_id,
        tx_hash=chain_receipt["tx_hash"],
        block_number=chain_receipt["block_number"],
        explorer_url=chain_receipt["explorer_url"]
    )


@app.get("/api/v1/telemetry-logs")
def get_live_audit_feed():
    """Provides recent access telemetry to the React SOC Dashboard."""
    return telemetry_audit_store
