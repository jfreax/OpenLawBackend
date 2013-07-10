#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sqlite3
from flask import Flask, request, session, g, redirect, url_for, \
     abort, render_template, flash
from contextlib import closing

from openlawDb import connect_db


# configuration
DEBUG = True
SECRET_KEY = 'development key'

# main app
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
			and Laws.slug == "%s"' % slug)
	entries = [dict(headline=row[0], depth=row[1]) for row in cur.fetchall()]
	return render_template('heads', heads=entries)

@app.route('/<slug>/<int:i>')
def show_law_text(slug, i):
	cur = g.db.execute('\
		select \
			Law_Texts.text \
		from \
			Laws, \
			Law_Texts \
		where \
			Law_Texts.law_id == Laws.id and \
			Laws.slug == "%s" and \
			Law_Texts.head_id == %i' % (slug, i))
	text = cur.fetchall()[0][0]
	return text

if __name__ == '__main__':
	app.run()

