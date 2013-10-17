#!/usr/bin/env python
# -*- coding: utf-8 -*-

from flask import Flask, Response, request, session, g, redirect, url_for, \
     abort, render_template, flash, jsonify, make_response
from contextlib import closing
from urllib import unquote
from functools import wraps
import thread
import sqlite3

from db import connect_db

from piwik_config import *
from piwikapi.tracking import PiwikTracker
from piwikapi.tests.request import FakeRequest


# Tracking method #
###################
piwikrequest = FakeRequest(headers)
piwiktracker = PiwikTracker(PIWIK_SITE_ID, piwikrequest)
piwiktracker.set_api_url(PIWIK_TRACKING_API_URL)

def do_piwik(ip, url, title):
    piwiktracker.set_ip(ip)
    piwiktracker.set_token_auth(AUTH_TOKEN_STRING)
    piwiktracker.set_url("http://"+url)
    title = title.encode('ascii',"ignore")
    piwiktracker.do_track_page_view(title)

# Decorations #
###############
def support_jsonp(f):
    """Wraps JSONified output for JSONP"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        callback = request.args.get('callback', False)
        if callback:
            content = str(callback) + '(' + str(f().data) + ')'
            return app.response_class(content, mimetype='application/json; charset=utf-8')
        else:
            return f(*args, **kwargs)
    return decorated_function
 

# Main app #
############
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
@support_jsonp
def show_all_laws():
    cur = g.db.execute('select slug, short_name, long_name from Laws')
    entries = [dict(slug=row[0], short=row[1], long=row[2]) for row in cur.fetchall()]

    thread.start_new_thread(do_piwik, (request.remote_addr, headers["SERVER_NAME"]+"/laws", "laws"))
    
    response = Response(response = render_template('laws', laws=entries),
            status = 200,
            mimetype = "application/json; charset=utf-8")
    return response


@app.route('/law/<slug>')
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
    fetchs = cur.fetchone()
    if fetchs is None:
        abort(404)
    
    law_name = fetchs[0]
    thread.start_new_thread(do_piwik,
        (request.remote_addr, headers["SERVER_NAME"]+"/"+slug, u"%s - %s" % (slug, law_name.replace(u'\\', u'')))
    )

    return render_template('heads', heads=entries)


@app.route('/law/<slug>/<int:i>')
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
    fetchs = cur.fetchone()
    if fetchs is None:
        abort(404)

    text = fetchs[0]
    headline = fetchs[1]

    thread.start_new_thread(do_piwik, 
        (request.remote_addr, headers["SERVER_NAME"]+"/"+slug+"/"+str(i), u"%s - %s" % (slug, headline.replace(u'\\', u'')))
    )

    return text


@app.errorhandler(404)
def not_found(error):
    return make_response(
        jsonify( {
            'error': 'Not found',
            'code': '404' }
        ), 404)


if __name__ == '__main__':
    app.debug = True
    app.run()

