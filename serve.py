#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Production entry point.

Serves the app with waitress (a pure-Python, cross-platform WSGI server) instead
of Flask's development server. This is what the Windows service runs.

The app listens on 127.0.0.1:8013 and sits behind the Caddy reverse proxy, which
publishes it on the LAN under the /labels path. ProxyFix makes Flask honor the
X-Forwarded-* headers Caddy sends (notably X-Forwarded-Prefix), so url_for()
generates correct /labels/... links.
"""
from waitress import serve
from werkzeug.middleware.proxy_fix import ProxyFix
from app import create_app

app = create_app()
app.wsgi_app = ProxyFix(
    app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

if __name__ == '__main__':
    serve(app, host='127.0.0.1', port=8013, threads=8)
