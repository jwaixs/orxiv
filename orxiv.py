#!/usr/bin/env python
# -*- coding: utf-8 -*-

import feedparser
import re
import string
import os
import time
import pickle

arxiv_groups = map(lambda elm : 'cat:' + elm, [
        'math.AG',
        'math.AT',
        'math.AP',
        'math.CT',
        'math.CA',
        'math.CO',
        'math.AC',
        'math.CV',
        'math.DG',
        'math.DS',
        'math.FA',
        'math.GM',
        'math.GN',
        'math.GT',
        'math.GR',
        'math.HO',
        'math.IT',
        'math.KT',
        'math.LO',
        'math.MP',
        'math.MG',
        'math.NT',
        'math.NA',
        'math.OA',
        'math.OC',
        'math.PR',
        'math.QA',
        'math.RT',
        'math.RA',
        'math.SP',
        'math.ST',
        'math.SG'])
arxiv_rss_url = r'http://export.arxiv.org/api/query?search_query=%s&sortBy=submittedDate&start=0&max_results=500' % string.join(arxiv_groups, '+OR+')
author_filter = [
        r'(Antonio|A\.)? (J\.)? ?Dur(a|á)n', 
        r'Noud Aldenhoven',
        r'Erik Koelink',
        r'Kenny De Commer',
        r'Wolter Groenevelt',
        r'Mourad E\. H\. Ismail',
        r'Pablo Roman',
        r'Ana M\. de los R[i,í]os',
        r'Maarten van Pruijssen',
        r'Stefan Kolb',
        r'Tom H\. Koornwinder',
        r'Rutger Kuyper',
        r'Michiel de Bondt',
        r'Gert Heckman',
        r'Landsman',
        r'Maarten Solleveld',
        r'Jord Boeijink',
        r'Walter D\. van Suijlekom',
        r'Kenier Castillo',
        r'Martijn Caspers',
        r'Tim de Laat']
title_filter = [
        r'[Q,q]uantum [G,g]roup',
        r'[O,o]rthogonal [P,p]olynomial',
        r'[M,m]atrix-[V,v]alued',
        r'Chebyshev [p,P]olynomials',
        r'Askey',
        r'Wilson',
        r'Koornwinder',
        r'Riemann [H,h]ypothesis',
        r'[H,h]ypergeometric [F,f]unctions',
        r'[H,h]ypergeometric [S,s]eries']
UPDATE_TIME = 60*60*12 # 12 hours


try:
    pfile = open('data.pkl', 'rwb')
    print 'Found pickle file, checking modification date...'
    t1 = os.path.getmtime('data.pkl')
    t2 = time.time()
    if t2 - t1 > UPDATE_TIME:
        print 'Feed file is too old, loading new articles on Arxiv...'
        feed = feedparser.parse(arxiv_rss_url)
        pickle.dump(feed, pfile)
    else:
        print 'Loading feed from pickle file...'
        feed = pickle.load(pfile)
except:
    print 'Create new pickle file...'
    pfile = open('data.pkl', 'wb')
    print 'Loading new articles on Arxiv...'
    feed = feedparser.parse(arxiv_rss_url)
    pickle.dump(feed, pfile)

pfile.close()

def joinFilter(filter_list):
    re_proof = map(lambda elm : '(' + elm + ')', filter_list)
    return string.join(re_proof, '|')

def filterFeedList(author_list, title_list):
    global feed

    author_filter = joinFilter(author_list)
    title_filter = joinFilter(title_list)

    ret = []
    for item in feed['items']:
        authors = string.join([ elm['name'] for elm in item.authors ], ', ')
        if re.search(author_filter, authors):
            ret.append(item)
        elif re.search(title_filter, item.title):
            ret.append(item)

    return ret

def printArticle(item):
    authors = string.join([ elm['name'] for elm in item.authors ], ', ')
    print 'Author:', authors
    print 'Title:', item.title
    print 'Link:', item.link

if __name__ == '__main__':
    results = set(filterFeedList(author_filter, title_filter))
    print 'Found %i hits:' % len(results)
    for result in results:
        print '-----'
        printArticle(result)
