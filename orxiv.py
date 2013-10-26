#!/usr/bin/env python
# -*- coding: utf-8 -*-

import feedparser
import re
import string
import os
import time
import datetime
from dateutil import rrule
import pickle
import sys
import argparse
import urllib2

MAX_RESULTS = 500
DOWNLOAD_DIR = './new_papers'

def create_arxiv_rss_url(groups, start_date, end_date, start_item, 
        max_results):
    
    def parse_time(t):
        return str(t.year) + '%02d' % t.month + '%02d' % t.day + '200000'

    ret = r'http://export.arxiv.org/api/query?'
    ret += r'search_query='
    ret += r'submittedDate:[%s+TO+%s]' % \
            (parse_time(start_date), parse_time(end_date))
    ret += r'+AND+(%s)' % string.join(groups, '+OR+')
    ret += r'&sortBy=submittedDate' 
    ret += r'&start=%i' % start_item
    ret += r'&max_results=%i' % max_results

    return ret

def get_feed(feed_url):
    feed = feedparser.parse(feed_url)
    return feed

def joinFilter(filter_list):
    re_proof = map(lambda elm : '(' + elm + ')', filter_list)
    return string.join(re_proof, '|')

def filterFeedList(feed_items, author_list, title_list):
    global feed

    author_filter = joinFilter(author_list)
    title_filter = joinFilter(title_list)

    ret = []
    for item in feed_items:
        authors = string.join([ elm['name'] for elm in item.authors ], ', ')
        if re.search(author_filter, authors):
            ret.append(item)
        elif re.search(title_filter, item.title):
            ret.append(item)

    return ret

def printArticle(item):
    authors = string.join([ elm['name'] for elm in item.authors ], ', ')
    print 10*'-'
    print 'Author:', authors
    print 'Title:', item.title

    def parse_time(t):
        stime = time.strptime(t, '%Y-%m-%dT%H:%M:%SZ')
        return datetime.datetime.fromtimestamp(time.mktime(stime))

    print 'Published:', parse_time(item.published)
    print 'Summary:', item.summary
    print 'Last updated:', parse_time(item.updated)
    print 'Link:', item.link


def get_daily_feed(dt):
    feed_url = create_arxiv_rss_url(arxiv_groups, dt-datetime.timedelta(days=1), dt, 0, MAX_RESULTS)
    return get_feed(feed_url)['items']

def get_feeds(startdate, enddate):
    ret_feeds = {}
    for dt in rrule.rrule(rrule.DAILY, dtstart=startdate, until=enddate):
        print 'Getting items from ArXiv of day: %i-%i-%i...' % \
                (dt.year, dt.month, dt.day),
        day_feeds = get_daily_feed(dt)
        ret_feeds[datetime.date(dt.year, dt.month, dt.day)] = day_feeds
        print '%i items.' % len(day_feeds)
        time.sleep(1)
    return ret_feeds

def update_feed(feed_file_name):
    '''Doesn't work!'''
    try:
        pfile = open(feed_file_name, 'r')
        print 'update feed'
        feed = pickle.load(pfile)
        last_day = datetime.date.fromtimestamp(
                os.path.getmtime(feed_file_name)) \
            + datetime.timedelta(days=1)
        today = datetime.date.today()
        feed += get_feed_dates(last_day, today)
        #for dt in rrule.rrule(rrule.DAILY, dtstart=last_day, until=today):
        #    feed[datetime.date(dt.year, dt.month, dt.day)] = get_daily_feed(dt)
        #    print dt - datetime.timedelta(days=1)
        pfile.close()
        pfile = open(feed_file_name, 'w')
        pickle.dump(feed, pfile)
    except:
        print 'creating new feed'
        pfile = open(feed_file_name, 'w')
        feed = { datetime.date.today() : get_daily_feed(datetime.date.today()) }
        pickle.dump(feed, pfile)
        pfile.close()

    return feed

def reporthook(blocknum, blocksize, totalsize):
    '''http://stackoverflow.com/questions/13881092/download-progressbar-for-python-3'''
    readsofar = blocknum * blocksize
    if totalsize > 0:
        percent = readsofar * 1e2 / totalsize
        s = "\r%5.1f%% %*d / %d" % (
            percent, len(str(totalsize)), readsofar, totalsize)
        sys.stderr.write(s)
        if readsofar >= totalsize: # near the end
            sys.stderr.write("\n")
    else: # total size is unknown
        sys.stderr.write("read %d\n" % (readsofar,))


def download_file(furl, fdest):
    TOTAL_BLOCKS = 70

    try:
        print 'Start downloading article.'
        with open(fdest, 'w') as output:
            ul = urllib2.urlopen(furl)
            file_size = int(ul.info().getheaders("Content-Length")[0])
            chunk_size = file_size / TOTAL_BLOCKS
            bytes_read = 0

            blocks = 0
            process = 0.0
            while True:
                data = ul.read(chunk_size)
                bytes_read += len(data)
                sys.stdout.write('#')
                sys.stdout.flush()
                output.write(data)
                
                blocks += 1
                process += 1.0 / TOTAL_BLOCKS
                process = process if process < 1.0 else 1.0

                process_bar = '\r[{0}] {1}%'.format(
                    '#'*blocks + '-'*(TOTAL_BLOCKS - blocks), int(process*100))
                sys.stdout.write(process_bar)
                sys.stdout.flush()
                
                if len(data) < chunk_size:
                    sys.stdout.write(' done!\n')
                    sys.stdout.flush()
                    break

    except IOError:
        print 'An error occured!'
        return False

    return True

def download_article(furl, fdir, ftitle):
    if not os.path.isdir(fdir):
        os.makedirs(fdir)
    return download_file(furl, fdir + '/' + ftitle)
    

def downloadArticle(item):
    furl = item.link.replace('abs', 'pdf')
    ftitle = item.link.split('/abs/')[1] + '.pdf'
    return download_article(furl, DOWNLOAD_DIR, ftitle)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Orxiv - the ArXiv organiser.')
    parser.add_argument('num_days', metavar='N', type=int,
            help='the number of days to go back into the archive.')
    parser.add_argument('-a', '--auto_download', action='store_true',
            help='Automaticly download arxiv paper hits')
    args = parser.parse_args()

    ffile = open('categories', 'r')
    arxiv_groups = map(lambda elm : 'cat:' + elm[:-1], ffile.readlines())
    ffile.close()

    ffile = open('authors', 'r')
    author_filter = map(lambda elm : elm[:-1], ffile.readlines())
    ffile.close()

    ffile = open('titles', 'r')
    title_filter = map(lambda elm : elm[:-1], ffile.readlines())
    ffile.close()

    today = datetime.date.today() 
    last_date = today - datetime.timedelta(days=args.num_days)
    feeds = get_feeds(last_date, today)
    for date in sorted(feeds.keys()):
        filfeeds = filterFeedList(feeds[date], author_filter, title_filter)
        for article in filfeeds:
            printArticle(article)
            if args.auto_download:
                downloadArticle(article)

