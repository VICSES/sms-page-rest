import os
import base64
import importlib
import pytest

from moto import mock_dynamodb2
from moto.dynamodb2.models import dynamodb_backend2
from unittest.mock import patch

@pytest.fixture
def token_secret():
    return 'test'*16

@pytest.fixture
def b64_token_secret(token_secret):
    return str(base64.b64encode(bytes(token_secret, 'utf-8')), 'utf-8')


@pytest.fixture
def app(b64_token_secret):
    # Local import to allow testing of the import
    os.environ['TOKEN_SECRET'] = b64_token_secret
    import web
    importlib.reload(web.authenticate) # Required to prevent caching of secret
    app = web.app
    app.testing = True
    return app

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def dynamodb():
    with mock_dynamodb2():
        yield dynamodb_backend2

@pytest.fixture
def contacts_table(dynamodb):
    return dynamodb.create_table("contacts",schema=[
        {u'KeyType': u'HASH', u'AttributeName': u'phone_number'}
    ])

@pytest.fixture
def unit_table(dynamodb):
    return dynamodb.create_table("unit",schema=[
        {u'KeyType': u'HASH', u'AttributeName': u'name'}
    ])

