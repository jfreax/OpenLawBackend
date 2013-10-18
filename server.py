#!/usr/bin/env python
# -*- coding: utf-8 -*-

from flask import Flask, Response, request, session, g, redirect, url_for, \
     abort, render_template, flash, jsonify, make_response
from flaskmimerender import mimerender
from contextlib import closing
from urllib import unquote
from functools import wraps
import thread
import sqlite3
import json

from db import connect_db

from config import *
from piwikapi.tracking import PiwikTracker
from piwikapi.tests.request import FakeRequest


# Tracking method
piwikrequest = FakeRequest(headers)
piwiktracker = PiwikTracker(PIWIK_SITE_ID, piwikrequest)
piwiktracker.set_api_url(PIWIK_TRACKING_API_URL)

def do_piwik(ip, url, title):
    piwiktracker.set_ip(ip)
    piwiktracker.set_token_auth(AUTH_TOKEN_STRING)
    piwiktracker.set_url("http://"+url)
    title = title.encode('ascii',"ignore")
    piwiktracker.do_track_page_view(title)


# Decoration to support jsonp
# See: https://gist.github.com/aisipos/1094140
def support_jsonp(f):
    """Wraps JSONified output for JSONP"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        callback = request.args.get('callback', False)
        if callback:
            data = f(*args,**kwargs)
            if isinstance(data, Response):
                data = data.data
            else:
                data = str(data)
            content = str(callback) + '(' + data + ')'
            return app.response_class(content, mimetype='application/javascript')
        else:
            return f(*args, **kwargs)
    return decorated_function

render_json = jsonify
render_html = lambda data : data

# Initialize flask
app = Flask(__name__)
app.config.from_object(__name__)
app.config['SERVER_NAME'] = SERVER_NAME


# Spin up and tear down database connection
@app.before_request
def before_request():
    g.db = connect_db()


@app.teardown_request
def teardown_request(exception):
    db = getattr(g, 'db', None)
    if db is not None:
        db.close()


# Get a list of all available countries
# Only id is needed for the other ressources
# TODO use db to query available countries
@app.route('/land', methods=['GET'])
@support_jsonp
@mimerender(
    default = 'json',
    json = render_json,
)
def show_all_lands():
    count_cur = g.db.execute('select count() from Laws')
    count = count_cur.fetchone()[0]

    ret = {
        'data': [
              {'id': '1',
               'name': 'Bundesgesetze',
               'name-en': 'German Federal Law',
               'count': count
              }
            ]
        }
    return ret


# Show all law codes from specified country
# Get all available id's with /land
# TODO Abort with code 404 when country id does not exist
#
# Pagination is supported. 10 items per page is standard.
# Abort with code 400 when page number is invalid
@app.route('/land/<int:id>/laws', methods=['GET'])
@support_jsonp
@mimerender(
    default = 'json',
    json = render_json,
)
def show_all_laws(id):
    try:
        items = int(request.args.get('items', 10))
        page = int(request.args.get('page', -1))
    except ValueError:
        abort(400)
        
    if page == -1:
        items = -1
  
    cur = g.db.execute('\
        select slug, short_name, long_name \
        from   Laws \
        limit ?,?', [page*items, items])
    
    ret = { "paging": {}, }
    ret['data'] = [ [row[1].replace(u'\\', u''),
                     row[0].replace(u'\\', u''),
                     row[2].replace(u'\\', u'')] for row in cur.fetchall()]

    if len(ret['data']) == 0:
        abort(400)
    if page > 0:
        ret['paging']['previous'] = url_for('.show_all_laws', id=id, page=page-1, items=items, _external=True)
    if len(ret['data']) == items:
        ret['paging']['next'] = url_for('.show_all_laws', id=id, page=page+1, items=items, _external=True)      

    thread.start_new_thread(do_piwik, (request.remote_addr, headers["SERVER_NAME"]+"/laws", "laws"))
    return ret


# Get all headlines from specified country and law code slug.
# Slugs are a short name unique for every law code
# Query all available slugs with 'show_all_laws'
@app.route('/land/<int:id>/laws/<slug>', methods=['GET'])
@support_jsonp
@mimerender(
    default = 'json',
    json = render_json,
)
def show_head_of_law(id, slug):
    cur = g.db.execute('\
        select Laws.long_name \
        from   Laws \
        where  Laws.slug == ?', [slug])
    fetchs = cur.fetchone()
    if fetchs is None:
        abort(404)
    
    law_name = fetchs[0]
    thread.start_new_thread(do_piwik,
        (request.remote_addr, headers["SERVER_NAME"]+"/"+slug, u"%s - %s" % (slug, law_name.replace(u'\\', u'')))
    )
  
    cur = g.db.execute('\
        select Law_Heads.id, Law_Heads.headline, Law_Heads.depth \
        from   Laws, Law_Heads \
        where  Law_Heads.law_id == Laws.id and \
               Laws.slug == ?', [slug])

    ret = {}
    ret['data'] = [ {'id': row[0],
                     'name': row[1].replace(u'\\', u''),
                     'depth': row[2],} for row in cur.fetchall()]
    return ret


# Get law text from one specific law code.
# Use headline id from 'show_head_of_law'.
@app.route('/land/<int:id>/laws/<slug>/<int:i>', methods=['GET'])
@support_jsonp
@mimerender(
    default = 'json',
    json = render_json,
    html = render_html,
)
def show_law_text(id, slug, i):
    cur = g.db.execute('\
        select Law_Texts.text, Law_Heads.headline \
        from   Laws, Law_Texts, Law_Heads \
        where  Law_Texts.law_id == Laws.id and \
               Laws.slug == ? and \
               Law_Texts.head_id == ? \
        limit 1', [slug, i])
    fetchs = cur.fetchone()
    if fetchs is None:
        abort(404)

    text = fetchs[0]
    headline = fetchs[1]

    thread.start_new_thread(do_piwik, 
        (request.remote_addr, headers["SERVER_NAME"]+"/"+slug+"/"+str(i), u"%s - %s" % (slug, headline.replace(u'\\', u'')))
    )

    return { 'data': text }


# Custom http return code pages
@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify( { 'error': 'Not found' } ), 404)
  
@app.errorhandler(400)
def not_found(error):
    return make_response(jsonify( { 'error': 'Bad request' } ), 400)

if __name__ == '__main__':
    app.debug = True
    app.run()

