#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os, sys, re
import codecs
from itertools import chain
import lxml.etree, lxml.html

import openlawDb

# Configuration
base_url = "http://www.gesetze-im-internet.de/"

# Open db connection
db = openlawDb.connect_db()

# Delete old entries
openlawDb.init_db()

# Root node
root_alphabet = lxml.html.parse(base_url+"aktuell.html").getroot()

# Get list of all laws
# (name, fulltitle, slug/link)
def getAllLaws():
    ret = []

    alphabet = root_alphabet.cssselect("#container .alphabet")
    for el in alphabet:
        if el.attrib.has_key('href'):
            alphabet_elem = lxml.html.parse(base_url+el.attrib['href']).getroot()

            link_elem = alphabet_elem.cssselect("#paddingLR12 p a")
            title_elem = alphabet_elem.cssselect("#paddingLR12 p a abbr")

            for (el_link, el_title) in zip(link_elem, title_elem):
                if el_link.attrib.has_key('href') and not el_link.attrib['href'].endswith('.pdf'):
                    ret.append((
                            re.escape(el_title.text.lstrip(' ').rstrip(' ')),
                            re.escape(el_title.attrib['title']),
                            el_link.attrib['href'][2:-11]
                        ))
    return ret


# Get headline + text for specific law
def getLawText(slug, html):
    # Fix: for laws without headlines

    # Initialize helper variables
    fakeLinkIDs = []
    i = 0
    first = True

    # Return variables
    lawHeads = []
    lawTexts = []

    trs = html.xpath("//div[@id='paddingLR12']/table/tr")
    if len(trs) == 0:
        trs = html.xpath("//div[@id='paddingLR12']")

    for tr in trs:
        i = i+1

        tds = tr.xpath("child::td")
        if len(tds) == 0:
            text = ""
        else:
            text = tr.xpath("child::td/descendant::text()")[-1]

        # Skip if headline text is empty, unless its the first entry
        tmp_text = text.replace(u' ', u'').replace(u'\xa0', u'')
        if not first and not tmp_text:
            continue

        ###
        # HEADLINE
        ###
        depth = 0
        if len(tds) == 0:
            head_link = tr.xpath("child::table/a/attribute::href")[0]
            head_root = lxml.html.parse(base_url+slug+"/"+head_link).getroot()
        else:
            depth = len(tds)
            if len(tds) < 3:
                colspan = tds[-1].xpath("attribute::colspan")[0]
                depth = 4 - int(colspan)

            if first:
                if text[0] != u"§" and not text.startswith("Art"):
                    depth = 1


            head_link = tds[-1].xpath("child::a/attribute::href")[0]
            head_root = lxml.html.parse(base_url+slug+"/"+head_link).getroot()

        # Append headline
        if '#' in head_link and not first:
            lawHeads.append((-depth, text))
        else:
            lawHeads.append((depth, text))

        ###
        # TEXT
        ###

        # Its only a link to the whole law text rather to one part of it
        if '#' in head_link and not first:
            fakeLinkIDs.append(i)
            continue

        # Cleaning
        for bad in head_root.xpath("//a[text()='Nichtamtliches Inhaltsverzeichnis']"):
            bad.getparent().remove(bad)
        for bad in head_root.xpath("//div[contains(@class, 'jnheader')]"):
            bad.getparent().remove(bad)
        for tag in head_root.xpath('//*[@class]'):
            # For each element with a class attribute, remove that class attribute
            tag.attrib.pop('class')


        headHtml_elem = head_root.cssselect("#paddingLR12")


        # Write "link" to real first chapters
        if len(fakeLinkIDs) != 0:
            for fake in fakeLinkIDs:
                lawTexts.append("%%%i%%" % i)
            fakeLinkIDs = []
        else:
            # Write text
            lawTexts.append(lxml.etree.tostring(headHtml_elem[0]))

        if first:
            first = False

    return lawHeads, lawTexts


if __name__ == '__main__':

    # Debug
    #slug = "aa_g"
    #law_index_html = lxml.html.parse(base_url+slug+"/index.html").getroot()
    #heads, texts = getLawText(slug, law_index_html)
    #exit(0)

    # First, fetch links to all laws + short name and full name
    laws = getAllLaws()

    # Iter throu' all laws
    i = 1
    lawIter = chain(laws);
    while True:
        try:
            name, title, slug = lawIter.next()
        except StopIteration:
            # TODO
            break

        print "Insert: %s" % slug

        # Add laws
        db.execute('insert into Laws (slug, short_name, long_name) values (?, ?, ?)',
             [slug, name, title])

        # Get headlines and law text
        law_index_html = lxml.html.parse(base_url+slug+"/index.html").getroot()
        heads, texts = getLawText(slug, law_index_html)
        i = 0;
        for head, text in zip(heads, texts):
            db.execute('insert into Law_Heads (id, law_id, depth, headline) values \
                (?, \
                 (select id from Laws where slug = "%s"), \
                 ?, \
                 ? \
                )' % slug,
                [i, head[0], head[1]])

            db.execute('insert into Law_Texts (law_id, head_id, text) values \
                ((select id from Laws where slug = "%s"), \
                  ?, ? \
                )' % slug,
                [i, text])

            i += 1     

        # Flush database
        db.commit()
    