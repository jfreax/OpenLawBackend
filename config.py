#!/usr/bin/env python
# -*- coding: utf-8 -*-

SERVER_NAME = '127.0.0.1:5000'


# Piwik
AUTH_TOKEN_STRING = "secret"
PIWIK_SITE_ID = 2
PIWIK_TRACKING_API_URL = "http://piwik.jdsoft.de/piwik.php"

headers = {
    'HTTP_USER_AGENT': 'OpenLaw API Server',
    'SERVER_NAME': 'api.openlaw.jdsoft.de',
    'HTTPS': False,
}