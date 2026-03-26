"""
Twilio SMS alert module for missing person AI system.
Sends real-time SMS when wandering / critical risk is detected.
"""
import os
import time
from datetime import datetime

# Twilio credentials from environment
TWILIO_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_FROM = os.environ.get("TWILIO_FROM_NUMBER")
ALERT_TO = os.environ.get("ALERT_PHONE_NUMBER")

# Cooldown: don't send more than 1 SMS per 5 minutes
_last_alert_time: float = 0
COOLDOWN_SECONDS = 300  # 5 minutes


def send_sms_alert(person_id: str, distance_km: float, risk_label: str) -> bool:
    """
    Sends an SMS alert via Twilio when wandering is detected.
    Returns True if sent, False if skipped (cooldown) or credentials missing.
    """
    global _last_alert_time

    if not all([TWILIO_SID, TWILIO_TOKEN, TWILIO_FROM, ALERT_TO]):
        print("WARNING: Twilio credentials not configured — SMS not sent.")
        return False

    now = time.time()
    if now - _last_alert_time < COOLDOWN_SECONDS:
        remaining = int(COOLDOWN_SECONDS - (now - _last_alert_time))
        print(f"SMS cooldown: {remaining}s remaining — skipping alert.")
        return False

    try:
        from twilio.rest import Client  # pyre-ignore[21]
        client = Client(TWILIO_SID, TWILIO_TOKEN)
        timestamp = datetime.now().strftime("%d %b %Y, %I:%M %p")
        message = (
            f"🚨 WANDERING ALERT!\n"
            f"Person: {person_id}\n"
            f"Distance: {distance_km:.2f} km from home\n"
            f"Status: {risk_label}\n"
            f"Time: {timestamp}\n"
            f"Dashboard: https://ai-missing-person-drift-detection.onrender.com"
        )
        client.messages.create(body=message, from_=TWILIO_FROM, to=ALERT_TO)
        _last_alert_time = now
        print(f"✅ SMS alert sent to {ALERT_TO} for {person_id}")
        return True
    except Exception as e:
        print(f"❌ SMS send failed: {e}")
        return False