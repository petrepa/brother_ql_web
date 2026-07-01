#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Production entry point.

Serves the app with waitress (a pure-Python, cross-platform WSGI server) instead
of Flask's development server. This is what the Windows service runs. Listening
on port 80 makes the UI reachable at e.g. http://prp-tower.local/ with no port.
"""
from waitress import serve
from app import create_app

app = create_app()

if __name__ == '__main__':
    serve(app, host='0.0.0.0', port=80, threads=8)
