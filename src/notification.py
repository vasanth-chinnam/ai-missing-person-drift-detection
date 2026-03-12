import smtplib
import os
from email.mime.text import MIMEText

SENDER_EMAIL = os.environ.get("ALERT_SENDER_EMAIL", "vasanthchinnam0@gmail.com")
APP_PASSWORD = os.environ.get("ALERT_APP_PASSWORD", "1234567890")
RECEIVER_EMAIL = os.environ.get("ALERT_RECEIVER_EMAIL", "23eg107b14@anuarg.edu.in")


def send_alert(location, risk):

    message = f"""
    ALERT: Possible wandering detected

    Location: {location}
    Risk Score: {risk}
    """

    msg = MIMEText(message)

    msg["Subject"] = "Missing Person Alert"
    msg["From"] = SENDER_EMAIL
    msg["To"] = RECEIVER_EMAIL

    try:
        server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        server.login(SENDER_EMAIL, APP_PASSWORD)
        server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())
        server.quit()
        print(f"Alert sent to {RECEIVER_EMAIL}")
    except Exception as e:
        print(f"Failed to send alert: {e}")