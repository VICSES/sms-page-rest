import os
from flask import Flask

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
