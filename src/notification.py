"""
Twilio SMS alert module for missing person AI system.
Sends real-time SMS when wandering / critical risk is detected.
"""
import os
import time
import sys
from datetime import datetime

# Twilio credentials from environment
TWILIO_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_FROM = os.environ.get("TWILIO_FROM_NUMBER")
ALERT_TO = os.environ.get("ALERT_PHONE_NUMBER")

# Cooldown: don't send more than 1 SMS per 1 second (for testing)
_last_alert_time: float = 0
COOLDOWN_SECONDS = 1 


def _log(msg: str):
    sys.stderr.write(f"SMS_DEBUG: {msg}\n")
    sys.stderr.flush()


def send_sms_alert(person_id: str, distance_km: float, risk_label: str, supabase_client=None) -> bool:
    """
    Sends an SMS alert via Twilio when wandering is detected.
    Uses Supabase (if provided) to persist the cooldown across server restarts.
    """
    if not all([TWILIO_SID, TWILIO_TOKEN, TWILIO_FROM, ALERT_TO]):
        _log(f"Missing credentials! SID={bool(TWILIO_SID)}, TOKEN={bool(TWILIO_TOKEN)}, FROM={bool(TWILIO_FROM)}, TO={bool(ALERT_TO)}")
        return False
    
    now_ts = int(time.time())
    last_sent = 0

    # Try to get last sent time from Supabase to survive server restarts
    if supabase_client:
        try:
            res = supabase_client.table("system_metadata").select("value").eq("key", "last_sms_time").execute()
            if res.data:
                last_sent = int(res.data[0]["value"])
        except Exception:
            _log("Could not fetch cooldown from Supabase, using default 0")

    if now_ts - last_sent < COOLDOWN_SECONDS:
        remaining = COOLDOWN_SECONDS - (now_ts - last_sent)
        _log(f"Cooldown active: {remaining}s remaining — skipping alert.")
        return False

    # IMPORTANT: Update last_sent BEFORE the attempt to prevent rapid fire if Twilio fails
    if supabase_client:
        try:
            supabase_client.table("system_metadata").upsert({"key": "last_sms_time", "value": str(now_ts)}).execute()
        except Exception as e:
            _log(f"Warning: Could not update Supabase cooldown: {e}")

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
        _log(f"Attempting to send to {ALERT_TO}...")
        client.messages.create(body=message, from_=TWILIO_FROM, to=ALERT_TO)
        _log(f"✅ SMS successfully handed to Twilio for {person_id}")
        return True
    except Exception as e:
        _log(f"❌ SMS send failed: {e}")
        return False