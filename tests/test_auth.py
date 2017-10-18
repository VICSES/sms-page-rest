import pytest

import dynamodb

import importlib
import os 
import base64
import json
import jwt
import time
from urllib.parse import urlparse, parse_qs
from typing import NamedTuple, Set
import responses


def import_succeeds():
    try:
        m = importlib.import_module('web.authenticate')
        importlib.reload(m) # Required to reexecute module
        return True
    except:
        pass
    return False

def test_secret():
    # We mest supply an environment variable 'TOKEN_SECRET'
    # It must be a base64 encoded string
    # It must decode to a 512 bit key, 64 bytes
    # This is tested at the base of the module, upon import
    #
    # We use a helper function to test this, to contain the import scope

    assert os.environ.get('TOKEN_SECRET') is None
    assert import_succeeds() == False

    os.environ['TOKEN_SECRET'] = str(base64.b64encode(b'tooshort'), 'utf-8')
    assert import_succeeds() == False

    os.environ['TOKEN_SECRET'] = '$isnotvalidb64'*100
    assert import_succeeds() == False

    os.environ['TOKEN_SECRET'] = str(base64.b64encode(b'A'*64), 'utf-8')
    assert import_succeeds() == True

    os.environ['TOKEN_SECRET'] = str(base64.b64encode(b'A'*63), 'utf-8')
    assert import_succeeds() == False

@responses.activate
def test_get_token(client, b64_token_secret, mocker):
    dynamodb.delete('test')
    dynamodb.create('test')
    dynamodb.add_role('test', 'ARole', ['read'])
    dynamodb.add_role('test', 'BRole', ['read', 'dance'])
    dynamodb.add_role('test', 'Doggone', ['dog'])

    lookup = mocker.patch('web.authenticate.lookup_member')

    missing_token_resp = {
        "error": {
            "code": "InvalidAuthenticationToken",
            "message": "Bearer access token is empty.",
            "innerError": {
                "request-id": "80554f33-d7c0-4a94-bebf-3b3f1ee6d2d4",
                "date": "2017-10-29T08:25:08"
            }
        }
    }

    bad_token_resp = {
        "error": {
            "code": "InvalidAuthenticationToken",
            "message": "CompactToken parsing failed with error code: -2147184105",
            "innerError": {
                "request-id": "e541876a-8621-4ea4-844d-15dfbf547626",
                "date": "2017-10-29T09:21:23"
            }
        }
    }

    altered_token_resp = {
        "error": {
            "code": "InvalidAuthenticationToken",
            "message": "Access token validation failure.",
            "innerError": {
                "request-id": "4b4e162d-cb56-4937-995b-2032c8823e1a",
                "date": "2017-10-29T09:50:39"
            }
        }
    }

    userdata_resp = {
        "businessPhones"    : [ "61212341234" ],
        "displayName"       : "Two Names",
        "givenName"         : "Two",
        "surname"           : "Names",
        "jobTitle"          : "Volunteer",
        "mail"              : "test@test.com",
        "mobilePhone"       : "6144123123",
        "officeLocation"    : "Test", # unit
        "preferredLanguage" : "English",
        "userPrincipalName" : "ses123@members.ses.vic.gov.au",
        "id"                : "1234-5678-1234-5678"
    }

    lookup.return_value = {
            'member_id' : 123,
            'name' : "Test User",
            'unit' : 'Test',
            'roles' : '{"Role":"True"}',
    }

    # Good retrieve
    responses.add(responses.GET, 'https://graph.microsoft.com/v1.0/me',
            json=userdata_resp, status=200)
    access_bearer = "doesn't matter"
    headers = {'Authorization':"Bearer " + access_bearer}
    url_rsp = client.get('/authenticate', headers=headers)
    assert url_rsp.status_code == 200
    js = json.loads(url_rsp.data)
    assert len(js) == 1
    assert len(js.get('resource_token')) > 200
    jjwt = jwt.decode(js.get('resource_token'), verify=False)
    assert jjwt.get('exp') is not None

    # Missing authentication token
    responses.replace(responses.GET, 'https://graph.microsoft.com/v1.0/me',
            json=missing_token_resp, status=200)
    url_rsp = client.get('/authenticate')
    assert url_rsp.status_code == 403
    assert url_rsp.data == b'This service is for vicses members only.'

    # Bad format header
    responses.replace(responses.GET, 'https://graph.microsoft.com/v1.0/me',
            json=bad_token_resp, status=200)
    url_rsp = client.get('/authenticate', headers={'Authorization':'Bearer XXX'})
    assert url_rsp.status_code == 403
    assert url_rsp.data == b'This service is for vicses members only.'

    # Altered token
    responses.replace(responses.GET, 'https://graph.microsoft.com/v1.0/me',
            json=altered_token_resp, status=200)
    url_rsp = client.get('/authenticate', headers={'Authorization':'Bearer XXX'})
    assert url_rsp.status_code == 403
    assert url_rsp.data == b'This service is for vicses members only.'
    
    # member not found
    lookup.return_value = None
    responses.replace(responses.GET, 'https://graph.microsoft.com/v1.0/me',
            json=userdata_resp, status=200)
    headers = {'Authorization':"Bearer " + access_bearer}
    url_rsp = client.get('/authenticate', headers=headers)
    assert url_rsp.status_code == 403
    assert url_rsp.data == b'You must be authorized to use this service.'

    # ensure roles etc. are reflected in token
    lookup.return_value = {
            'member_id' : 123,
            'name' : "Test User",
            'unit' : 'Test',
            'roles' : '["ARole", "BRole", "Doggone"]',
    }
    url_rsp = client.get('/authenticate', headers=headers)
    assert url_rsp.status_code == 200
    js = json.loads(url_rsp.data)
    assert len(js) == 1
    assert len(js.get('resource_token')) > 200
    token_secret = base64.b64decode(b64_token_secret)
    jjwt = jwt.decode(js.get('resource_token'), token_secret, algorithms=['HS256'], issuer='sms-page')
    assert len(jjwt) == 7

    assert jjwt.get('exp') is not None
    assert jjwt.get('member_id') == '123'
    assert jjwt.get('name') == 'Test User'
    assert jjwt.get('unit') == 'Test'
    assert jjwt.get('iss') == 'sms-page'
    assert set(jjwt.get('roles')) == set(["ARole", "BRole", "Doggone"])
    assert set(jjwt.get('permissions')) == set(["read", "dance", "dog"])


def test_auth_middleware(client, b64_token_secret):
    from web.authenticate import AuthMiddleware

    outer = {'called':False,'cargs':[]}
    def app_func(*args):
        outer['called']=True
        outer['cargs']=args

    ret = AuthMiddleware(app_func)

    # Missing header
    ret([], "start")
    assert outer['called'] == True
    assert outer['cargs'] == ([], "start")

    # Valid token
    token_secret = base64.b64decode(b64_token_secret)
    tok_time = time.time()+10
    tok_content = {"key":"value", 'iss':'sms-page', 'exp':tok_time}
    tok = jwt.encode(tok_content, token_secret, algorithm='HS256')
    print("TSTS", token_secret)
    outer = {'called':False,'cargs':[]}
    ret({'HTTP_AUTHORIZATION':'Bearer '+str(tok, 'utf-8')}, "start")
    assert outer['called'] == True
    assert outer['cargs'][0].get('authentication.credentials') is not None
    assert len(outer['cargs'][0]['authentication.credentials']) == 3
    assert outer['cargs'][0]['authentication.credentials'].get('key') == 'value'
    assert outer['cargs'][0]['authentication.credentials'].get('iss') == 'sms-page'
    assert outer['cargs'][0]['authentication.credentials'].get('exp') == tok_time

    # Missing bearer
    outer = {'called':False,'cargs':[]}
    ret({'HTTP_AUTHORIZATION':str(tok, 'utf-8')}, "start")
    assert outer['cargs'][0].get('authentication.credentials') is None

    # Bad token
    tok = jwt.encode({"key":"value", 'iss':'sms-page', 'exp':time.time()+10}, 'bad', algorithm='HS256')
    outer = {'called':False,'cargs':[]}
    ret({'HTTP_AUTHORIZATION':'Bearer '+str(tok, 'utf-8')}, "start")
    assert outer['cargs'][0].get('authentication.credentials') is None

    # Expired token
    tok = jwt.encode({"key":"value", 'iss':'sms-page', 'exp':time.time()-10}, token_secret, algorithm='HS256')
    outer = {'called':False,'cargs':[]}
    ret({'HTTP_AUTHORIZATION':'Bearer '+str(tok, 'utf-8')}, "start")
    assert outer['cargs'][0].get('authentication.credentials') is None


def test_authorized(app, client, mocker):
    # authorized is a function decorator
    from web.authorize import authorized, Credentials, own_unit, has_role, has_all, has_permission

    get_creds = mocker.patch('web.authorize.Predicate.get_credentials')

    get_creds.return_value = Credentials(
            member_id = 123,
            name = 'Test User',
            unit = 'Test', 
            roles = set({'foo':'bar'}),
            permissions = set({'sausage','frankfurt'})
    )

    mf_ret = "MF"
    def mf(**kwargs):
        return mf_ret

    dec = authorized(own_unit())

    with app.test_request_context():
        assert dec(mf)(unit='Test') == "MF"
        assert dec(mf)(unit='NotTest') == ({'error':'Authorization','detail':["Not the member's unit"]}, 403)
        assert dec(mf)()[1] == 403

        assert authorized(has_role('foo'))(mf)() == "MF"
        assert authorized(has_role('frog'))(mf)() == ({'error':'Authorization','detail':["Required role not found"]}, 403)
        assert authorized(has_role('foo', 'frog', 'flip'))(mf)() == "MF"

        comb = authorized(own_unit(), has_role('foo'))
        assert comb(mf)(unit='Test') == "MF"
        assert comb(mf)(unit='NotTest') == "MF"

        comb = authorized(own_unit(), has_role('frog'))
        assert comb(mf)(unit='Test') == "MF"
        assert comb(mf)(unit='NotTest') == ({'error':'Authorization','detail':["Not the member's unit", "Required role not found"]}, 403)

        comb = authorized(has_all(own_unit(), has_role('foo')))
        assert comb(mf)(unit='Test') == "MF"
        assert comb(mf)(unit='NotTest') == ({'error':'Authorization','detail':["Not the member's unit"]}, 403)

        comb = authorized(has_all(own_unit(), has_role('frog')))
        assert comb(mf)(unit='Test') == ({'error':'Authorization','detail':["Required role not found"]}, 403)
        assert comb(mf)(unit='NotTest') == ({'error':'Authorization','detail':["Not the member's unit"]}, 403)

        assert authorized(has_permission('sausage'))(mf)() == "MF"
        assert authorized(has_permission('sausage','soup'))(mf)() == "MF"
        assert authorized(has_permission('soup'))(mf)() == ({'error':'Authorization','detail':["Required permission not found"]}, 403)
        assert authorized(has_permission('frankfurt'))(mf)() == "MF"

        # has_unit can fish the unit out of data for PUT and POST requests
        form_dat = authorized(own_unit())
        with app.test_request_context(method='GET', data={'unit':'Test'}):
            assert form_dat(mf)() == ({'error':'Authorization','detail'  :["Not the member's unit"]}, 403)
        with app.test_request_context(method='POST', data={'unit':'Test'}):
            assert form_dat(mf)() == "MF"
        with app.test_request_context(method='PUT', data={'unit':'Test'}):
            assert form_dat(mf)() == "MF"
        with app.test_request_context(method='GET', data={'unit':'Other'}):
            assert form_dat(mf)() == ({'error':'Authorization','detail'  :["Not the member's unit"]}, 403)
        with app.test_request_context(method='POST', data={'unit':'Other'}):
            assert form_dat(mf)() == ({'error':'Authorization','detail'  :["Not the member's unit"]}, 403)
        with app.test_request_context(method='PUT', data={'unit':'Other'}):
            assert form_dat(mf)() == ({'error':'Authorization','detail'  :["Not the member's unit"]}, 403)

        # has_unit can act in a post-check manner
        # If we have a GET request and can't determine the unit the
        # execution continues and we check for the unit on the way out
        assert authorized(own_unit())(mf)() == ({'error':'Authorization','detail'  :["Not the member's unit"]}, 403)
        mf_ret = ({'unit':'Test'}, 200)
        assert authorized(own_unit())(mf)() == mf_ret

        # Multiple tests - OR
        mf_ret = ({'unit':'Test'}, 200)
        pc = authorized(own_unit(), has_permission('sausage'))
        assert pc(mf)() == mf_ret
        pc = authorized(own_unit(), has_permission('soup'))
        assert pc(mf)() == mf_ret
        mf_ret = "FM"
        pc = authorized(own_unit(), has_permission('sausage'))
        assert pc(mf)() == "FM"
        pc = authorized(own_unit(), has_permission('soup'))
        assert pc(mf)() == ({'error':'Authorization','detail':["Required permission not found", "Not the member's unit"]}, 403)

        # Multiple tests - AND
        mf_ret = ({'unit':'Test'}, 200)
        pc = authorized(has_all(own_unit(), has_permission('sausage')))
        assert pc(mf)() == mf_ret
        pc = authorized(has_all(own_unit(), has_permission('soup')))
        assert pc(mf)() == ({'error':'Authorization','detail':["Required permission not found"]}, 403)
        mf_ret = "FM"
        pc = authorized(has_all(own_unit(), has_permission('sausage')))
        assert pc(mf)() == ({'error':'Authorization','detail':["Not the member's unit"]}, 403)
