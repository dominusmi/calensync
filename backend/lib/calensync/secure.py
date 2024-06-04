import base64
import json
import os
import secrets

import boto3
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from calensync.utils import is_local

ENCRYPTION_KEY = None


def fetch_ssm_parameter(session: boto3.Session, parameter_arn: str):
    """
    Fetches the value of an SSM parameter.

    :param session: boto3 session
    :param parameter_arn: The ARN of the SSM parameter
    :return: The value of the SSM parameter
    """
    # Create an SSM client
    ssm = session.client('ssm')  # Specify your AWS region
    post_colon = parameter_arn.split(':')[-1]
    # need to skip the prefix "parameter" which is assigned to all parameters
    parameter_name = post_colon[len('parameter'):]

    try:
        # Get the parameter
        response = ssm.get_parameter(
            Name=parameter_name,
            WithDecryption=True  # Set to True to decrypt SecureString parameters
        )
        # Extract the parameter value
        parameter_value = response['Parameter']['Value'].encode()
        return parameter_value
    except ssm.exceptions.ParameterNotFound:
        print(f"Parameter {parameter_name} not found.")
        return None
    except Exception as e:
        print(f"Unexpected error when fetching parameter {parameter_name}: {e}")
        return None


def get_encryption_key(boto3_session: boto3.Session):
    global ENCRYPTION_KEY
    if is_local():
        if not os.getenv('ENCRYPTION_KEY_ARN'):
            return b'q'*32

    if ENCRYPTION_KEY is None:
        secret_string = fetch_ssm_parameter(boto3_session, os.environ['ENCRYPTION_KEY_ARN'])
        ENCRYPTION_KEY = base64.b64decode(secret_string)

    return ENCRYPTION_KEY


def encrypt_credentials(credentials: dict, boto3_session: boto3.Session) -> str:
    key = get_encryption_key(boto3_session)

    # Encrypt a message
    nonce = secrets.token_bytes(12)  # GCM mode needs 12 fresh bytes every time
    ciphertext = nonce + AESGCM(key).encrypt(nonce, json.dumps(credentials).encode(), b'')
    # base64 encode it to be able to then transform it to string
    ciphertext = base64.b64encode(ciphertext).decode()
    return ciphertext


def decrypt_credentials(encrypted_credentials: str, boto3_session: boto3.Session) -> dict:
    key = get_encryption_key(boto3_session)
    ciphertext = base64.b64decode(encrypted_credentials)
    # Decrypt (raises InvalidTag if using wrong key or corrupted ciphertext)
    msg = AESGCM(key).decrypt(ciphertext[:12], ciphertext[12:], b'')
    return json.loads(msg)
