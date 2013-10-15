#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sqlite3
from flask import Flask, request, session, g, redirect, url_for, \
     abort, render_template, flash
from contextlib import closing
import thread

from openlawDb import connect_db
from piwikAuth import getAuthToken
from urllib import unquote

from piwikapi.tracking import PiwikTracker
from piwikapi.tests.request import FakeRequest

# Config
PIWIK_SITE_ID = 2
PIWIK_TRACKING_API_URL = "http://piwik.jdsoft.de/piwik.php"

# Simple piwik tracking setup
headers = {
    'HTTP_USER_AGENT': 'OpenLaw API Server',
    'SERVER_NAME': 'api.openlaw.jdsoft.de',
    'HTTPS': False,
}

piwikrequest = FakeRequest(headers)
piwiktracker = PiwikTracker(PIWIK_SITE_ID, piwikrequest)
piwiktracker.set_api_url(PIWIK_TRACKING_API_URL)
AUTH_TOKEN_STRING = getAuthToken();

# Tracking method
def do_piwik(ip, url, title):
	piwiktracker.set_ip(ip)
	piwiktracker.set_token_auth(AUTH_TOKEN_STRING)
	piwiktracker.set_url("http://"+url)
	title = title.encode('ascii',"ignore")
	piwiktracker.do_track_page_view(title)

# Main app
app = Flask(__name__)
app.config.from_object(__name__)


@app.before_request
def before_request():
	g.db = connect_db()

@app.teardown_request
def teardown_request(exception):
	db = getattr(g, 'db', None)
	if db is not None:
		db.close()

@app.route('/laws')
def show_all_laws():
	cur = g.db.execute('select slug, short_name, long_name from Laws')
	entries = [dict(slug=row[0], short=row[1], long=row[2]) for row in cur.fetchall()]

	thread.start_new_thread(do_piwik, (request.remote_addr, headers["SERVER_NAME"]+"/laws", "laws"))

	return render_template('laws', laws=entries)

@app.route('/<slug>')
def show_head_of_law(slug):
	cur = g.db.execute('\
		select \
			Law_Heads.headline, \
			Law_Heads.depth \
		from \
			Laws, \
			Law_Heads \
		where \
			Law_Heads.law_id == Laws.id \
			and Laws.slug == ?', [slug])
	entries = [dict(headline=row[0], depth=row[1]) for row in cur.fetchall()]

	cur = g.db.execute('\
		select \
			Laws.long_name \
		from \
			Laws \
		where \
			Laws.slug == ?', [slug])
	law_name = cur.fetchall()[0][0]
	thread.start_new_thread(do_piwik,
		(request.remote_addr, headers["SERVER_NAME"]+"/"+slug, u"%s - %s" % (slug, law_name.replace(u'\\', u'')))
	)

	return render_template('heads', heads=entries)

@app.route('/<slug>/<int:i>')
def show_law_text(slug, i):
	cur = g.db.execute('\
		select \
			Law_Texts.text, \
			Law_Heads.headline \
		from \
			Laws, \
			Law_Texts, \
			Law_Heads \
		where \
			Law_Texts.law_id == Laws.id and \
			Laws.slug == ? and \
			Law_Heads.law_id == ? and \
			Law_Texts.head_id == ?', [slug, i, i])
	fetchs = cur.fetchall()
	text = fetchs[0][0]
	headline = fetchs[0][1]

	thread.start_new_thread(do_piwik, 
		(request.remote_addr, headers["SERVER_NAME"]+"/"+slug+"/"+str(i), u"%s - %s" % (slug, headline.replace(u'\\', u'')))
	)

	return text

if __name__ == '__main__':
	app.run()

