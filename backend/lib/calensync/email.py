import time

import boto3
from botocore.exceptions import ClientError

from calensync.log import get_logger

logger = get_logger("email")


def send_email(session, sender, recipient, aws_region, subject, body_html, base_delay=1, max_attempts=3):
    """
    Send an email using Amazon SES.
    :param session: boto3.Session to use
    :param sender: Email address of the sender
    :param recipient: Email address of the recipient
    :param aws_region: AWS region where SES is available and used
    :param subject: Subject line of the email
    :param body_html: The email body in HTML format
    :param base_delay: base delay for exponential backoff
    :param max_attempts: max number of attempts
    """
    client = session.client('ses', region_name=aws_region)

    # Try to send the email
    for i in range(max_attempts):
        try:
            response = client.send_email(
                Destination={
                    'ToAddresses': [recipient],
                },
                Message={
                    'Body': {
                        'Html': {
                            'Charset': "UTF-8",
                            'Data': body_html,
                        }
                    },
                    'Subject': {
                        'Charset': "UTF-8",
                        'Data': subject,
                    },
                },
                Source=sender,
            )
            return True
        except ClientError as e:
            logger.warn("Attempt {}: {}".format(i + 1, e.response['Error']['Message']))
            time.sleep(base_delay * 2 ** i)  # Exponential backoff

    logger.error(f"Failed to send email {subject}\n{body_html} to {sender}")
    return False


def send_trial_ending_email(session, email: str):
    sender = "no-reply@calensync.live"
    recipient = email
    aws_region = "eu-north-1"
    subject = "Your Calensync Trial Period is Ending"
    body_html = """<html>
                <head></head>
                <body>
                    <p>Hello there,</p>
                    <p>We hope you've enjoyed using Calensync</p>
                    <p>Your trial period is ending today, please consider <a href='https://calensync.live/login'>subscribing</a> to continue using our services without interruption.</p><br><br>
                    <p>Have a great day,</p>
                    <div>Ed (Reach out at <a href = "mailto:ed@calensync.live">ed@calensync.live</a>)</div>
                </body>
                </html>
                """

    logger.info(f"Sending trial ending email to {email}")
    return send_email(session, sender, recipient, aws_region, subject, body_html)


def send_account_to_be_deleted_email(session, email: str):
    sender = "no-reply@calensync.live"
    recipient = email
    aws_region = "eu-north-1"
    subject = "Your Calensync synchronizations will soon be deleted"
    body_html = """<html>
            <head></head>
            <body>
                <p>Hello there,</p><br>
                <p>We're soon going to delete your Calensync account if you do not subscribe to a plan.</p><br>
                <p>If you want to continue using our services, we encourage you to <a href='https://calensync.live/login'>subscribe</a> as soon as possible to avoid any interruption in our services.</p><br><br>
                <p>Have a great day,</p><br>
                <div>Ed (Reach out at <a href = "mailto:ed@calensync.live">ed@calensync.live</a>)</div>
            </body>
            </html>
            """
    return send_email(session, sender, recipient, aws_region, subject, body_html)
