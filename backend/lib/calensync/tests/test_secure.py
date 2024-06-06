from unittest.mock import patch

import cryptography.exceptions

from calensync.secure import decrypt_credentials
from calensync.tests.fixtures import *


@pytest.fixture()
def with_encryption_key(boto_session):
    ssm = boto_session.client('ssm')
    response = ssm.put_parameter(
        Name='/encryption-key/name',
        Description='description of parameter',
        Type='String',
        Overwrite=True,
        Value='1234' * 8
    )
    account_id = boto_session.client('sts', region_name='us-east-1').get_caller_identity().get('Account')
    arn = f"arn:aws:ssm:{boto_session.region_name}:{account_id}:parameter/encryption-key/name"
    os.environ['ENCRYPTION_KEY_ARN'] = arn


class TestEncryptDecryptCredentials:
    @staticmethod
    def test_encrypt_valid_credentials(boto_session, with_encryption_key):
        ciphertext = encrypt_credentials({"test": "123", "of": "321"}, boto_session)
        decrypted = decrypt_credentials(ciphertext, boto_session)
        assert decrypted == {"test": "123", "of": "321"}

