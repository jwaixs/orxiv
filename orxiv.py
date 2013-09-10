#!/usr/bin/env python
# -*- coding: utf-8 -*-

import feedparser
import re
import string
import os
import time
import datetime
import pickle

ffile = open('categories', 'r')
arxiv_groups = map(lambda elm : 'cat:' + elm[:-1], ffile.readlines())
ffile.close()

arxiv_rss_url = r'http://export.arxiv.org/api/query?search_query=%s&sortBy=submittedDate&start=0&max_results=500' % string.join(arxiv_groups, '+OR+')

ffile = open('authors', 'r')
author_filter = map(lambda elm : elm[:-1], ffile.readlines())
ffile.close()

ffile = open('titles', 'r')
title_filter = map(lambda elm : elm[:-1], ffile.readlines())
ffile.close()

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

    def parse_time(t):
        stime = time.strptime(t, '%Y-%m-%dT%H:%M:%SZ')
        return datetime.datetime.fromtimestamp(time.mktime(stime))

    print 'Published:', parse_time(item.published)
    print 'Last updated:', parse_time(item.updated)
    print 'Link:', item.link

if __name__ == '__main__':
    results = list(set(filterFeedList(author_filter, title_filter)))
    results.sort(key=lambda item : item.updated)
    print 'Found %i hits:' % len(results)
    for result in results:
        print '-----'
        printArticle(result)
