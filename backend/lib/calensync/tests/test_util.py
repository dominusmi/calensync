import json
from unittest.mock import MagicMock, patch

import googleapiclient.errors
import pytest

from calensync.database.model import User, EmailDB
from calensync.tests.fixtures import db
from calensync.utils import prefetch_get_or_none, google_error_handling_with_backoff, BackoffException


class TestPrefetchOrNone:
    @staticmethod
    def test_exists(db):
        user_db = User().save_new()
        EmailDB(email="test@test.com", user=user_db).save_new()

        result = prefetch_get_or_none(
            EmailDB.select().where(EmailDB.email == "test@test.com"),
            User.select()
        )
        assert isinstance(result, EmailDB)

    @staticmethod
    def test_doesnt_exists(db):
        user_db = User().save_new()
        EmailDB(email="test@test.com", user=user_db).save_new()

        result = prefetch_get_or_none(
            EmailDB.select().where(EmailDB.email == "testing@test.com"),
            User.select()
        )
        assert result is None


class TestGoogleExceptionWithBackoff:
    @staticmethod
    def test_normal():
        i = [0]

        def _inner():
            i[0] += 1

        google_error_handling_with_backoff(_inner)
        assert i[0] == 1

    @staticmethod
    def test_backoff_without_json():
        i = [0]
        resp = MagicMock()
        resp.status = 429
        resp.reason = 'Rate Limit Exceeded'
        resp.get.return_value = ''

        def _inner():
            i[0] += 1
            raise googleapiclient.errors.HttpError(resp, content=b"")

        with pytest.raises(BackoffException):
            with patch("calensync.utils.sleep") as sleep:
                google_error_handling_with_backoff(_inner)

        assert i[0] == 4

    @staticmethod
    def test_backoff_with_json():
        i = [0]
        resp = MagicMock()
        resp.status = 429
        resp.get.return_value = 'application/json'

        def _inner():
            i[0] += 1
            raise googleapiclient.errors.HttpError(resp, content=json.dumps({'error': {'errors': [{'reason': 'rateLimitExceeded'}]}}).encode())

        with pytest.raises(BackoffException):
            with patch("calensync.utils.sleep") as sleep:
                google_error_handling_with_backoff(_inner)

        assert i[0] == 4

    @staticmethod
    def test_success_after_one_retry():
        i = [0]
        resp = MagicMock()
        resp.status = 429
        resp.reason = 'Rate Limit Exceeded'
        resp.get.return_value = ''

        def _inner():
            if i[0] == 1:
                return
            i[0] += 1
            raise googleapiclient.errors.HttpError(resp, content=b"")

        with patch("calensync.utils.sleep") as sleep:
            google_error_handling_with_backoff(_inner)

        assert i[0] == 1

    @staticmethod
    def test_unhandled_error():
        i = [0]
        resp = MagicMock()
        resp.status = 429
        resp.reason = 'Rate Limit Exceeded'

        def _inner():
            i[0] += 1
            raise RuntimeError()

        with pytest.raises(RuntimeError):
            with patch("calensync.utils.sleep") as sleep:
                google_error_handling_with_backoff(_inner)

        assert i[0] == 1
