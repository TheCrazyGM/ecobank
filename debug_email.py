from app import create_app
from app.extensions import mail
from flask_mail import Message
import sys

app = create_app()


def test_email(recipient):
    print(f"Attempting to send email to {recipient}...")
    print(f"MAIL_SERVER: {app.config.get('MAIL_SERVER')}")
    print(f"MAIL_PORT: {app.config.get('MAIL_PORT')}")
    print(f"MAIL_USERNAME: {app.config.get('MAIL_USERNAME')}")
    print(f"MAIL_USE_TLS: {app.config.get('MAIL_USE_TLS')}")

    with app.app_context():
        try:
            msg = Message(
                subject="[EcoBank] Debug Email",
                sender=app.config["ADMINS"][0],
                recipients=[recipient],
                body="If you are reading this, your email configuration is correct!",
            )
            mail.send(msg)
            print("SUCCESS: Email sent!")
        except Exception as e:
            print(f"FAILURE: Could not send email.\nError: {e}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python debug_email.py <recipient_email>")
        sys.exit(1)

    test_email(sys.argv[1])
