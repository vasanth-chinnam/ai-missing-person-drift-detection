"""
Alert Notification System
===========================
Sends real-time alerts via:
  - Email  (SMTP / Gmail)
  - SMS    (Twilio)
  - In-app (stores alert in JSON log for frontend polling)

Usage:
    from src.alerts import AlertSystem
    alerts = AlertSystem()
    alerts.send(person_id="P001", risk_level="HIGH",
                dist_km=1.8, lat=17.435, lon=78.370)

Configuration (set as environment variables or .env file):
    ALERT_EMAIL_TO      = caregiver@example.com
    ALERT_EMAIL_FROM    = noreply@yourdomain.com
    SMTP_HOST           = smtp.gmail.com
    SMTP_PORT           = 587
    SMTP_USER           = your@gmail.com
    SMTP_PASS           = app_password_here

    TWILIO_SID          = ACxxxxxxxxxx
    TWILIO_TOKEN        = your_token
    TWILIO_FROM         = +1XXXXXXXXXX
    TWILIO_TO           = +91XXXXXXXXXX
"""

import os
import json
import logging
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Optional Twilio import ─────────────────────────────────────────────────
try:
    from twilio.rest import Client as TwilioClient
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False
    TwilioClient = None # type: ignore
    logger.info("Twilio not installed – SMS alerts disabled. pip install twilio")


ALERT_LOG_PATH = Path("data/alerts.json")
RISK_COLORS = {"LOW": "#22c55e", "MEDIUM": "#f59e0b", "HIGH": "#ef4444"}


class AlertSystem:
    """
    Central alert dispatcher. Checks cooldown to avoid alert storms.
    Default cooldown: 15 minutes between repeated alerts for the same person.
    """

    def __init__(self, cooldown_minutes: int = 15):
        self.cooldown_minutes = cooldown_minutes
        self._last_alert: dict[str, datetime] = {}
        ALERT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        if not ALERT_LOG_PATH.exists():
            ALERT_LOG_PATH.write_text("[]")

    # ── Public API ─────────────────────────────────────────────────────────

    def send(self, person_id: str, risk_level: str,
             dist_km: float, lat: float, lon: float,
             extra_info: str = "") -> dict:
        """
        Dispatch alerts for a given person/risk combination.
        Returns a summary dict of what was sent.
        """
        if risk_level == "LOW":
            return {"sent": False, "reason": "risk_level_low"}

        if not self._cooldown_ok(person_id, risk_level):
            return {"sent": False, "reason": "cooldown_active"}

        alert = self._build_alert(person_id, risk_level, dist_km, lat, lon, extra_info)
        results = {}

        results["in_app"] = self._log_alert(alert)
        results["email"]  = self._send_email(alert)
        results["sms"]    = self._send_sms(alert)

        self._last_alert[f"{person_id}_{risk_level}"] = datetime.now()
        logger.info(f"Alert sent – {person_id} {risk_level}: {results}")
        return {"sent": True, "alert": alert, "channels": results}

    def get_recent_alerts(self, n: int = 20) -> list:
        """Return the N most recent in-app alerts (for the dashboard)."""
        try:
            data = json.loads(ALERT_LOG_PATH.read_text())
            return sorted(data, key=lambda x: x["timestamp"], reverse=True)[:n]
        except Exception:
            return []

    def send_emergency(self, person_id: str, dist_km: float,
                       lat: float, lon: float,
                       owner_phone: str = "", owner_email: str = "") -> dict:
        """
        Send EMERGENCY alert – bypasses cooldown entirely.
        Uses dynamic owner_phone/owner_email if provided.
        """
        alert = self._build_alert(person_id, "EMERGENCY", dist_km, lat, lon,
                                  "CRITICAL: Risk score reached 100%!")
        alert["risk_level"] = "EMERGENCY"
        results = {}
        results["in_app"] = self._log_alert(alert)

        # Try dynamic email first, fall back to env var
        if owner_email:
            results["email"] = self._send_email_to(alert, owner_email)
        else:
            results["email"] = self._send_email(alert)

        # Try dynamic phone first, fall back to env var
        if owner_phone:
            results["sms"] = self._send_sms_to(alert, owner_phone)
        else:
            results["sms"] = self._send_sms(alert)

        logger.warning(f"🚨 EMERGENCY ALERT – {person_id}: {results}")
        return {"sent": True, "alert": alert, "channels": results}

    # ── Internal helpers ───────────────────────────────────────────────────

    def _cooldown_ok(self, person_id: str, risk_level: str) -> bool:
        key = f"{person_id}_{risk_level}"
        last = self._last_alert.get(key)
        if last is None:
            return True
        elapsed = (datetime.now() - last).total_seconds() / 60
        return elapsed >= self.cooldown_minutes

    def _build_alert(self, person_id, risk_level, dist_km, lat, lon, extra_info):
        return {
            "id":          f"{person_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "person_id":   person_id,
            "risk_level":  risk_level,
            "dist_km":     round(dist_km, 2),
            "latitude":    lat,
            "longitude":   lon,
            "timestamp":   datetime.now().isoformat(),
            "extra_info":  extra_info,
            "maps_link":   f"https://maps.google.com/?q={lat},{lon}",
            "message":     self._format_message(person_id, risk_level, dist_km, lat, lon),
        }

    def _format_message(self, person_id, risk_level, dist_km, lat, lon):
        return (
            f"⚠️ ALERT – {risk_level} RISK\n"
            f"Person: {person_id}\n"
            f"Distance from home: {dist_km:.2f} km\n"
            f"Location: {lat:.5f}, {lon:.5f}\n"
            f"Maps: https://maps.google.com/?q={lat},{lon}\n"
            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

    def _log_alert(self, alert: dict) -> bool:
        """Append alert to local JSON log (polled by frontend)."""
        try:
            data = json.loads(ALERT_LOG_PATH.read_text())
            data.append(alert)
            data = data[-500:]   # Keep last 500 alerts only
            ALERT_LOG_PATH.write_text(json.dumps(data, indent=2))
            return True
        except Exception as e:
            logger.error(f"Failed to log alert: {e}")
            return False

    def _send_email(self, alert: dict) -> bool:
        """Send HTML email via SMTP. Requires env vars to be set."""
        to_addr   = os.getenv("ALERT_EMAIL_TO")
        from_addr = os.getenv("ALERT_EMAIL_FROM")
        smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        smtp_port = int(os.getenv("SMTP_PORT", 587))
        smtp_user = os.getenv("SMTP_USER")
        smtp_pass = os.getenv("SMTP_PASS")

        if not all([to_addr, from_addr, smtp_user, smtp_pass]):
            logger.info("Email credentials not configured – skipping email alert")
            return False

        color = RISK_COLORS.get(alert["risk_level"], "#888")
        html_body = f"""
        <div style="font-family:sans-serif;max-width:480px;margin:0 auto">
          <div style="background:{color};color:#fff;padding:16px 24px;border-radius:8px 8px 0 0">
            <h2 style="margin:0">⚠️ {alert['risk_level']} RISK ALERT</h2>
          </div>
          <div style="border:1px solid #ddd;border-top:none;padding:24px;border-radius:0 0 8px 8px">
            <p><strong>Person:</strong> {alert['person_id']}</p>
            <p><strong>Distance from home:</strong> {alert['dist_km']:.2f} km</p>
            <p><strong>Time:</strong> {alert['timestamp']}</p>
            <p><a href="{alert['maps_link']}" style="background:{color};color:#fff;padding:10px 20px;border-radius:6px;text-decoration:none">
              📍 View on Map
            </a></p>
          </div>
        </div>
        """
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"[ALERT] {alert['risk_level']} Risk – {alert['person_id']}"
        msg["From"] = from_addr or ""
        msg["To"] = to_addr or ""
        msg.attach(MIMEText(alert["message"], "plain"))
        msg.attach(MIMEText(html_body, "html"))

        try:
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()
                server.login(smtp_user or "", smtp_pass or "")
                server.sendmail(from_addr or "", to_addr or "", msg.as_string())
            return True
        except Exception as e:
            logger.error(f"Email send failed: {e}")
            return False

    def _send_sms(self, alert: dict) -> bool:
        """Send SMS via Twilio. Requires TWILIO_* env vars and pip install twilio."""
        if not TWILIO_AVAILABLE:
            return False

        sid   = os.getenv("TWILIO_SID")
        token = os.getenv("TWILIO_TOKEN")
        from_ = os.getenv("TWILIO_FROM")
        to    = os.getenv("TWILIO_TO")

        if not all([sid, token, from_, to]):
            logger.info("Twilio credentials not configured – skipping SMS alert")
            return False

        sms_body = (
            f"ALERT: {alert['risk_level']} RISK\n"
            f"Person {alert['person_id']} is {alert['dist_km']}km from home.\n"
            f"{alert['maps_link']}"
        )
        try:
            if TwilioClient is not None:
                client = TwilioClient(sid or "", token or "")
                client.messages.create(body=sms_body, from_=from_ or "", to=to or "")
                return True
            return False
        except Exception as e:
            logger.error(f"Twilio SMS failed: {e}")
            return False

    def _send_email_to(self, alert: dict, to_email: str) -> bool:
        """Send email to a specific address (for emergency alerts)."""
        from_addr = os.getenv("ALERT_EMAIL_FROM", os.getenv("SMTP_USER", ""))
        smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        smtp_port = int(os.getenv("SMTP_PORT", 587))
        smtp_user = os.getenv("SMTP_USER")
        smtp_pass = os.getenv("SMTP_PASS")

        if not smtp_user or not smtp_pass:
            logger.info(f"SMTP credentials not configured – would send EMERGENCY email to {to_email}")
            print(f"\n🚨 EMERGENCY EMAIL would be sent to: {to_email}")
            print(f"   Subject: {alert.get('message', 'EMERGENCY ALERT')[:100]}")
            return False

        color = "#dc2626"  # Always red for emergency
        html_body = f"""
        <div style="font-family:sans-serif;max-width:480px;margin:0 auto">
          <div style="background:{color};color:#fff;padding:16px 24px;border-radius:8px 8px 0 0">
            <h2 style="margin:0">🚨 EMERGENCY ALERT – RISK 100%</h2>
          </div>
          <div style="border:1px solid #ddd;border-top:none;padding:24px;border-radius:0 0 8px 8px">
            <p><strong>Person:</strong> {alert['person_id']}</p>
            <p><strong>Distance from home:</strong> {alert['dist_km']:.2f} km</p>
            <p><strong>Time:</strong> {alert['timestamp']}</p>
            <p><a href="{alert['maps_link']}" style="background:{color};color:#fff;padding:10px 20px;border-radius:6px;text-decoration:none">
              📍 View Location NOW
            </a></p>
          </div>
        </div>
        """
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"🚨 EMERGENCY – {alert['person_id']} RISK 100%"
        msg["From"] = from_addr
        msg["To"] = to_email
        msg.attach(MIMEText(alert.get("message", ""), "plain"))
        msg.attach(MIMEText(html_body, "html"))

        try:
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.sendmail(from_addr, to_email, msg.as_string())
            return True
        except Exception as e:
            logger.error(f"Emergency email failed: {e}")
            return False

    def _send_sms_to(self, alert: dict, to_phone: str) -> bool:
        """Send SMS to a specific phone number (for emergency alerts)."""
        if not TWILIO_AVAILABLE:
            print(f"\n🚨 EMERGENCY SMS would be sent to: {to_phone}")
            print(f"   Message: Person {alert['person_id']} is {alert['dist_km']}km from home – RISK 100%!")
            return False

        sid   = os.getenv("TWILIO_SID")
        token = os.getenv("TWILIO_TOKEN")
        from_ = os.getenv("TWILIO_FROM")

        if not all([sid, token, from_]):
            logger.info(f"Twilio not fully configured – would send EMERGENCY SMS to {to_phone}")
            print(f"\n🚨 EMERGENCY SMS would be sent to: {to_phone}")
            return False

        sms_body = (
            f"🚨 EMERGENCY: {alert['person_id']} RISK 100%\n"
            f"Distance: {alert['dist_km']}km from home\n"
            f"Location: {alert['maps_link']}"
        )
        try:
            if TwilioClient is not None:
                client = TwilioClient(sid or "", token or "")
                client.messages.create(body=sms_body, from_=from_ or "", to=to_phone)
                return True
            return False
        except Exception as e:
            logger.error(f"Emergency SMS failed: {e}")
            return False
