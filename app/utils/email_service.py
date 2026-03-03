from flask_mail import Message
from app import mail
from threading import Thread
from flask import current_app

def send_async_email(app, msg):
    with app.app_context():
        mail.send(msg)

def send_email(to, subject, body):
    app = current_app._get_current_object()

    msg = Message(subject, recipients=[to], body=body)

    thread = Thread(target=send_async_email, args=(app, msg))
    thread.start()
    return True
