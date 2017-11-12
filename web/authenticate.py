# Copyright 2017 David Tulloh This file is part of sms-page-rest.
# sms-page-rest is free software, you can distribute or modify it
# under the terms of the GNU Affero General Public License (AGPL-3).

import os
import time
import re
import base64
import json
import jwt
import requests

from flask import Blueprint, request, jsonify

from web.models import lookup_member, lookup_role

# Authentication process is documented at git://sms-page/authentication.md

auth_pages = Blueprint('auth_pages', __name__)

# Secret key comes from env as a base64 string
# For good quality encryption we require a 512 bit key (64 bytes)
# We enforce this requirement
# A base64 digit represents 6 bits, so we need 86 digits
try:
    token_secret = base64.b64decode(os.environ['TOKEN_SECRET'], validate=True)
    if len(token_secret) < 64:
        raise EnvironmentError()
except Exception:
    # Could be token not found, not valid base64 or too short
    # This exception is not designed to be caught, we want to bail out
    raise EnvironmentError("The 'TOKEN_SECRET' environment variable must be supplied, it must be a base64 encoded string and it must be at least 86 characters long")


@auth_pages.route('/authenticate')
def gen_resource_token():
    access_bearer = request.headers.get('Authorization') # with Bearer text
    headers = {'Authorization':access_bearer}
    resource = "https://graph.microsoft.com/v1.0/me"
    resp = requests.get(resource, headers=headers)

    if resp.status_code != 200:
        return ('Cannot verify authorization token', resp.status_code)

    userdata = resp.json()
    # Unit supplied in userdata.get('officeLocation')

    valid = re.fullmatch(r'ses(\d+)@members\.ses\.vic\.gov\.au', userdata.get('userPrincipalName', ''))
    if valid:
        ses_id = valid.group(1)
    else:
        return ('This service is for vicses members only.', 403)

    member = lookup_member(ses_id)
    if member is None:
        return ('You must be authorized to use this service.', 403)

    roles = json.loads(member['roles'])
    permissions = set()
    for role in roles:
        try:
            permissions.update(lookup_role(role)['permissions'])
        except Exception:
            pass # Could have corruption, role without matching entry

    # Build authorization token
    # This uses an internal secret so cannot be duplicated or modified.
    # It can be validated without requiring any external resources.
    authorization = {
        'member_id'   : ses_id,
        'name'        : member['name'],
        'unit'        : member['unit'],
        'roles'       : roles,
        'permissions' : list(permissions),
        'iss'         : 'sms-page',
        'exp'         : int(time.time())+86400+86400, # Two days
    }
    token = jwt.encode(authorization, token_secret, algorithm='HS256')

    return jsonify({'resource_token':str(token, 'utf-8')})


class AuthMiddleware:
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        try:
            auth_header = environ['HTTP_AUTHORIZATION']
            if not auth_header[:7].lower() == "bearer ":
                raise ValueError("expected bearer authorization token")

            token_bstr = bytes(auth_header[7:], 'utf-8')
            token = jwt.decode(token_bstr, token_secret, algorithms=['HS256'], issuer='sms-page')
            # By default jwt verifies standard fields, exp and iss

            environ['authentication.credentials'] = token
        except Exception:
            pass # We just don't set 'authentication.credentials'

        return self.app(environ, start_response)
