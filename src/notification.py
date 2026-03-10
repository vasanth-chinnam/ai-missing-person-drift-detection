import smtplib
from email.mime.text import MIMEText

SENDER_EMAIL = "vasanthchinnam0@gmail.com"
APP_PASSWORD = "1234567890"
RECEIVER_EMAIL = "23eg107b14@anuarg.edu.in"


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

    server = smtplib.SMTP_SSL("smtp.gmail.com", 465)

    server.login(SENDER_EMAIL, APP_PASSWORD)

    server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())

    server.quit()