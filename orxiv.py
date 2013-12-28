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
import curses
from curses import panel


def download_file(furl, fdest, total_blocks=60):
    try:
        print 'Start downloading article.'
        with open(fdest, 'w') as output:
            ul = urllib2.urlopen(furl)
            file_size = int(ul.info().getheaders("Content-Length")[0])
            chunk_size = file_size / total_blocks
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
                    '#'*blocks + '-'*(total_blocks - blocks), int(process*100))
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

def get_daily_articles(dt, arxiv_groups, max_results=500):
    feed_url = create_arxiv_rss_url(
        arxiv_groups, dt-datetime.timedelta(days=1), dt, 0, max_results
    )

    articles = [] 
    for raw_feed in feedparser.parse(feed_url)['items']:
        articles.append(Article(raw_feed))

    return articles


class Menu(object):
    def __init__(self, items, stdscreen):
        self.window = stdscreen.subwin(0, 0)
        self.window.keypad(1)
        self.panel = panel.new_panel(self.window)
        self.panel.hide()
        panel.update_panels()

        self.position = 0
        self.items = items
        self.items.append(('Exit.', 'exit'))

    def navigate(self, n):
        self.position += n
        self.position = self.position % len(self.items)

    def display(self):
        self.panel.top()
        self.panel.show()
        self.window.clear()

        while True:
            self.window.refresh()
            curses.doupdate()
            cur_line = 1
            for index, item in enumerate(self.items):
                if index == self.position:
                    mode = curses.A_REVERSE
                else:
                    mode = curses.A_NORMAL
                msg = '%d. %s' % (index+1, item[0])
                
                for line in msg.split('\n'):
                    self.window.addstr(cur_line, 1, line.encode('utf-8'), mode)
                    cur_line += 1            
                #self.window.addstr(index+1, 1, msg.encode('utf-8'), mode)

            key = self.window.getch()

            if key in [curses.KEY_ENTER, ord('\n')]:
                if self.items[self.position][0] == 'Exit.':
                    break
                else:
                    self.items[self.position][1]()
            elif key == curses.KEY_UP:
                self.navigate(-1)
            elif key == curses.KEY_DOWN:
                self.navigate(1)

        self.window.clear()
        self.panel.hide()
        panel.update_panels()
        curses.doupdate()


class InfoPanel(object):
    def __init__(self, items, stdscreen):
        self.window = stdscreen.subwin(0, 0)
        self.window.keypad(1)
        self.panel = panel.new_panel(self.window)
        self.panel.hide()
        panel.update_panels()

        self.items = items

    def display(self):
        self.panel.top()
        self.panel.show()
        self.window.clear()

        while True:
            self.window.refresh()
            curses.doupdate()
            index = 1
            for subject, info in self.items:
                msg = '%s: %s' % (subject, info.replace('\n', '\n  '))
                for line in msg.split('\n'):
                    self.window.addstr(index, 1, line.encode('utf-8'), curses.A_NORMAL)
                    index += 1

            key = self.window.getch()

            if key in [curses.KEY_ENTER, ord('\n')]:
                break

        self.window.clear()
        self.panel.hide()
        panel.update_panels()
        curses.doupdate()


class Article():
    def __init__(self, raw_feed):
        if 'arxiv_comment' in raw_feed.keys():
            self.arxiv_comment = raw_feed['arxiv_comment']
        else:
            self.arxiv_comment = ''
        self.arxiv_primary_category = raw_feed['arxiv_primary_category']
        self.author = raw_feed['author']
        self.authors = [aut_dict['name'] for aut_dict in raw_feed['authors']]
        self.author_detail = raw_feed['author_detail']
        self.guidislink = raw_feed['guidislink']
        self.idnr = raw_feed['id']
        self.link = raw_feed['link']
        self.links = raw_feed['links']
        self.published = raw_feed['published']
        self.summary = raw_feed['summary']
        self.summary_detail = raw_feed['summary_detail']
        self.tags = raw_feed['tags']
        self.title = raw_feed['title']
        self.title_detail = raw_feed['title_detail']
        self.updated = raw_feed['updated']
        self.updated_parsed = raw_feed['updated_parsed']

    def downloadArticle(targetdir, targetfile):
        if not os.path.isdir(fdir):
            os.makedirs(fdir)
        furl = self.link.replace('abs', 'pdf')
        ftitle = self.link.split('/abs/')[1] + '.pdf'
        download_article(furl, fdir + '/' + ftitle)

    def printSmallSummary(self):
        return ', '.join(self.authors) + ' - ' + self.title + '.'

    def printBigSummary(self):
        return [
            ('Id', str(self.idnr)),
            ('Title', self.title),
            ('Authors', ', '.join(self.authors)),
            ('Published', str(self._parse_date(self.published))),
            ('Updated', str(self._parse_date(self.updated))),
            ('Summary', self.summary),
            ('Author_comment', self.arxiv_comment),
            ('Link', str(self.link))
        ]

    def _parse_date(self, t):
        stime = time.strptime(t, '%Y-%m-%dT%H:%M:%SZ')
        return datetime.datetime.fromtimestamp(time.mktime(stime))

    def _join_filter(self, filter_list):
        re_proof = map(lambda elm : '(' + elm + ')', filter_list)
        return string.join(re_proof, '|')

    def filterArticle(self, author_list, title_list):
        author_filter = self._join_filter(author_list)
        title_filter = self._join_filter(title_list)

        if re.search(author_filter, self.author) \
                or re.search(title_filter, self.title):
            return True
        else:
            return False

class OrxivObject(object):
    def __init__(self, stdscreen):
        self.screen = stdscreen
        curses.curs_set(0)
    
        startdate = datetime.datetime(2013, 12, 20, 0, 0)
        enddate = datetime.datetime(2013, 12, 26, 0, 0)
        articles = []

        for dt in rrule.rrule(rrule.DAILY, dtstart=startdate, until=enddate):
            articles += self.get_articles(dt)

        article_panels = []
        for article in articles:
            article_panel_items = article.printBigSummary()
            article_panels.append(InfoPanel(article_panel_items, self.screen))

        main_menu_items = []
        for i in range(len(article_panels)):
            main_menu_items.append(
                (articles[i].printSmallSummary(), article_panels[i].display)
            )
        main_menu = Menu(main_menu_items, self.screen)
        main_menu.display()

    def get_articles(self, dt):
        ffile = open('categories', 'r')
        arxiv_groups = map(lambda elm : 'cat:' + elm[:-1], ffile.readlines())
        ffile.close()
        
        ffile = open('authors', 'r')
        author_filter = map(lambda elm : elm[:-1], ffile.readlines())
        ffile.close()

        ffile = open('titles', 'r')
        title_filter = map(lambda elm : elm[:-1], ffile.readlines())
        ffile.close()

        return [ article for article in get_daily_articles(dt, arxiv_groups) 
            if article.filterArticle(author_filter, title_filter) ]


if __name__ == '__main__':
    curses.wrapper(OrxivObject)
        
    #ffile = open('categories', 'r')
    #arxiv_groups = map(lambda elm : 'cat:' + elm[:-1], ffile.readlines())
    #ffile.close()

    #articles = get_daily_articles(datetime.datetime(2013, 12, 23, 0, 0), arxiv_groups)
    #print articles[0].authors

        
#
#MAX_RESULTS = 500
#DOWNLOAD_DIR = './new_papers'
#
#
## save and load function for feeds
#FEEDS_FILE = './feeds.pkl'
#
#def save_feeds(feeds):
#    global global_changes
#
#    if global_changes:
#        pkl_file = open(FEEDS_FILE, 'w')
#        pickle.dump(feeds, pkl_file)
#        pkl_file.close()
#
#def load_feeds():
#    try:
#        pkl_file = open(FEEDS_FILE, 'r')
#        feeds = pickle.load(pkl_file)
#        pkl_file.close()
#        
#        return feeds
#    except:
#        return {}
#
#global_feeds = load_feeds()
#global_changes = False
#
#def create_arxiv_rss_url(groups, start_date, end_date, start_item, 
#        max_results):
#    
#    def parse_time(t):
#        return str(t.year) + '%02d' % t.month + '%02d' % t.day + '200000'
#
#    ret = r'http://export.arxiv.org/api/query?'
#    ret += r'search_query='
#    ret += r'submittedDate:[%s+TO+%s]' % \
#            (parse_time(start_date), parse_time(end_date))
#    ret += r'+AND+(%s)' % string.join(groups, '+OR+')
#    ret += r'&sortBy=submittedDate' 
#    ret += r'&start=%i' % start_item
#    ret += r'&max_results=%i' % max_results
#
#    return ret
#
#def get_feed(feed_url):
#    feed = feedparser.parse(feed_url)
#    return feed
#
#def joinfilter(filter_list):
#    re_proof = map(lambda elm : '(' + elm + ')', filter_list)
#    return string.join(re_proof, '|')
#
#def filterFeedList(feed_items, author_list, title_list):
#    global feed
#
#    author_filter = joinFilter(author_list)
#    title_filter = joinFilter(title_list)
#
#    ret = []
#    for item in feed_items:
#        authors = string.join([ elm['name'] for elm in item.authors ], ', ')
#        if re.search(author_filter, authors):
#            ret.append(item)
#        elif re.search(title_filter, item.title):
#            ret.append(item)
#
#    return ret
#
#def printArticle(item):
#    authors = string.join([ elm['name'] for elm in item.authors ], ', ')
#    print 10*'-'
#    print 'Author:', authors
#    print 'Title:', item.title
#
#    def parse_time(t):
#        stime = time.strptime(t, '%Y-%m-%dT%H:%M:%SZ')
#        return datetime.datetime.fromtimestamp(time.mktime(stime))
#
#    print 'Published:', parse_time(item.published)
#    print 'Summary:', item.summary
#    print 'Last updated:', parse_time(item.updated)
#    print 'Link:', item.link
#
#
#def get_daily_feed(dt):
#    feed_url = create_arxiv_rss_url(arxiv_groups, dt-datetime.timedelta(days=1), dt, 0, MAX_RESULTS)
#    return get_feed(feed_url)['items']
#
#def get_feeds(startdate, enddate, ignore_global=False):
#    global global_feeds
#    global global_changes
#    ret_feeds = {}
#
#    for dt in rrule.rrule(rrule.DAILY, dtstart=startdate, until=enddate):
#        if not dt in global_feeds.keys() or ignore_global:
#            print 'Getting items from ArXiv of day: %i-%i-%i...' % \
#                    (dt.year, dt.month, dt.day),
#            sys.stdout.flush()
#            day_feeds = get_daily_feed(dt)
#            global_feeds[dt] = day_feeds
#            ret_feeds[datetime.date(dt.year, dt.month, dt.day)] = day_feeds
#            print '%i items.' % len(day_feeds)
#            global_changes = True
#            time.sleep(1)
#        else:
#            print 'Already downloaded items from day: %i-%i-%i...' % \
#                (dt.year, dt.month, dt.day),
#            day_feeds = global_feeds[dt]
#            ret_feeds[datetime.date(dt.year, dt.month, dt.day)] = day_feeds
#            print '%i items.' % len(day_feeds)
#    return ret_feeds
#
#
#def download_article(furl, fdir, ftitle):
#    if not os.path.isdir(fdir):
#        os.makedirs(fdir)
#    return download_file(furl, fdir + '/' + ftitle)
#    
#
#def downloadArticle(item):
#    furl = item.link.replace('abs', 'pdf')
#    ftitle = item.link.split('/abs/')[1] + '.pdf'
#    return download_article(furl, DOWNLOAD_DIR, ftitle)
#
#
#if __name__ == '__main__':
#    global global_feeds
#
#    parser = argparse.ArgumentParser(description='Orxiv - the ArXiv organiser.')
#    parser.add_argument('num_days', metavar='N', type=int,
#            help='the number of days to go back into the archive.')
#    parser.add_argument('-a', '--auto_download', action='store_true',
#            help='Automaticly download arxiv paper hits')
#    parser.add_argument('-r', '--refresh', action='store_true',
#            help='Refresh the already downloaded items')
#    args = parser.parse_args()
#
#    ffile = open('categories', 'r')
#    arxiv_groups = map(lambda elm : 'cat:' + elm[:-1], ffile.readlines())
#    ffile.close()
#
#    ffile = open('authors', 'r')
#    author_filter = map(lambda elm : elm[:-1], ffile.readlines())
#    ffile.close()
#
#    ffile = open('titles', 'r')
#    title_filter = map(lambda elm : elm[:-1], ffile.readlines())
#    ffile.close()
#
#    today = datetime.date.today() 
#    last_date = today - datetime.timedelta(days=args.num_days)
#    feeds = get_feeds(last_date, today, ignore_global=args.refresh)
#    for date in sorted(feeds.keys()):
#        filfeeds = filterFeedList(feeds[date], author_filter, title_filter)
#        for article in filfeeds:
#            printArticle(article)
#            if args.auto_download:
#                downloadArticle(article)
#
#    save_feeds(global_feeds)
