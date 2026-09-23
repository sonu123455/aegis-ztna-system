import os
import numpy as np
import joblib
from sklearn.ensemble import IsolationForest

def generate_training_data(n_samples=1800):
    """
    Generates baseline behavioral telemetry for legitimate enterprise users:
    - Feature 1: Keystroke Cadence (IKT) in ms -> 140ms - 320ms normal range
    - Feature 2: Access Hour -> Centered around operational hours (7 AM - 11 PM)
    - Feature 3: Violation Counter -> 0 for trusted operators
    """
    np.random.seed(42)

    # Legitimate Cadence centered at 210ms (std dev = 35ms)
    normal_cadence = np.random.normal(loc=210, scale=35, size=n_samples)
    normal_cadence = np.clip(normal_cadence, 130, 340)

    # Access hours: distributed between 07:00 and 23:00
    normal_hours = np.random.normal(loc=15, scale=4, size=n_samples)
    normal_hours = np.clip(np.round(normal_hours), 7, 23)

    # Policy violations: 95% zero violations, 5% single accidental violation
    normal_violations = np.random.choice([0, 1], size=n_samples, p=[0.95, 0.05])

    return np.column_stack((normal_cadence, normal_hours, normal_violations))

def train_and_export(output_filename="ztna_model.joblib"):
    print("[*] Generating baseline behavioral biometrics dataset...")
    x_train = generate_training_data()

    print("[*] Training Isolation Forest model (150 decision trees)...")
    model = IsolationForest(
        n_estimators=150,
        contamination=0.08,
        random_state=42,
        bootstrap=False
    )
    model.fit(x_train)

    joblib.dump(model, output_filename)
    print(f"[+] Model saved to {output_filename}")
    return model

if __name__ == "__main__":
    train_and_export()
