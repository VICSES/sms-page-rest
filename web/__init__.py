# Copyright 2017 David Tulloh
# This file is part of sms-page-rest. sms-page-rest is free software,
# you can distribute or modify it under the terms of the AGPL-3 licence.

import os
from flask import Flask, jsonify

from web.authenticate import auth_pages, AuthMiddleware
from web.rest import rest_pages
from web.models import DecimalEncoder



class CORSMiddleware:
    def __init__(self, wrapapp):
        self.app = wrapapp

    def __call__(self, environ, start_response):
        def custom_start_response(status, headers, exc_info=None):
            headers.append(('Access-Control-Allow-Origin', '*'))
            headers.append(('Access-Control-Max-Age', '86400')) # 1 day
            headers.append(('Access-Control-Allow-Methods', 'POST, OPTIONS, GET, PUT, DELETE'))
            headers.append(('Access-Control-Allow-Headers', 'Authorization'))
            return start_response(status, headers, exc_info)
        return self.app(environ, custom_start_response)


app = Flask(__name__)
app.json_encoder = DecimalEncoder
app.register_blueprint(auth_pages)
app.register_blueprint(rest_pages)

app.wsgi_app = CORSMiddleware(app.wsgi_app)
app.wsgi_app = AuthMiddleware(app.wsgi_app)

@app.route('/')
def basic_info():
    github_page = 'https://github.com/VICSES/sms-page-rest'
    branch = 'master'
    info = {
        'brief' : 'This project provides a rest interface to the sms-page databases. It is not designed to be accessed manually.',
        'url' : github_page,
        'api-documentation' : '{}/blob/{}/api.md'.format(github_page, branch),
        'licence' : 'AGPL-3',
        'source-code' : '{}/tree/{}'.format(github_page, branch),
    }

    return jsonify(info)
