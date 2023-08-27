import json
import logging
import os
import sys

try:
    import hashlib
    #from hashlib import md5
    md5 = hashlib.md5
except ImportError:
    # pre 2.6/2.5
    from md5 import new as md5

import logging
import os
import subprocess
import sys
import urllib
try:
    # Py3
    from urllib.error import HTTPError
    from urllib.request import urlopen, urlretrieve, Request
    from urllib.parse import quote_plus
    from urllib.parse import urlencode
except ImportError:
    # Py2
    from urllib import quote_plus, urlretrieve  #TODO is this in urllib2?
    from urllib2 import urlopen, Request, HTTPError
    from urllib import urlencode


#import requests
from bs4 import BeautifulSoup


__version__ = '0.0.1'

log = logging.getLogger("eech")
log.setLevel(logging.DEBUG)
disable_logging = False
#disable_logging = True
if disable_logging:
    log.setLevel(logging.NOTSET)  # only logs; WARNING, ERROR, CRITICAL

ch = logging.StreamHandler()  # use stdio

formatter = logging.Formatter("logging %(process)d %(thread)d %(asctime)s - %(filename)s:%(lineno)d %(name)s - %(levelname)s - %(message)s")
ch.setFormatter(formatter)
log.addHandler(ch)

log.info('%s version %s', __name__, __version__)
log.info('Python %r on %r', sys.version, sys.platform)


is_win = sys.platform.startswith('win')

def urllib_get_url(url, headers=None):
    """
    @url - web address/url (string)
    @headers - dictionary - optional
    """
    log.debug('get_url=%r', url)
    #log.debug('headers=%r', headers)
    response = None
    try:
        if headers:
            request = Request(url, headers=headers)
        else:
            request = Request(url)  # may not be needed
        response = urlopen(request)
        url = response.geturl()  # may have changed in case of redirect
        code = response.getcode()
        #log("getURL [{}] response code:{}".format(url, code))
        result = response.read()
        return result
    finally:
        if response != None:
            response.close()

def safe_mkdir(newdir):
    result_dir = os.path.abspath(newdir)
    try:
        os.makedirs(result_dir)
    except OSError as info:
        if info.errno == 17 and os.path.isdir(result_dir):
            pass
        else:
            raise

cache_dir = os.environ.get('WIKI_CACHE_DIR', 'scraper_cache')
safe_mkdir(cache_dir)

def hash_url(url):
    m = md5()
    m.update(url.encode('utf-8'))
    return m.hexdigest()

# headers to emulate Firefox - actual headers from real browser
MOZILLA_FIREFOX_HEADERS = {
    #'HTTP_HOST': 'localhost:8000',
    'HTTP_USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0',
    'HTTP_ACCEPT': '*/*',
    'HTTP_ACCEPT_LANGUAGE': 'en-US,en;q=0.5',
    'HTTP_ACCEPT_ENCODING': 'gzip, deflate, br',
    'HTTP_SERVICE_WORKER': 'script',
    'HTTP_CONNECTION': 'keep-alive',
    'HTTP_COOKIE': 'js=y',  # could be problematic...
    'HTTP_SEC_FETCH_DEST': 'serviceworker',
    'HTTP_SEC_FETCH_MODE': 'same-origin',
    'HTTP_SEC_FETCH_SITE': 'same-origin',
    'HTTP_PRAGMA': 'no-cache',
    'HTTP_CACHE_CONTROL': 'no-cache'
}


def get_url(url, filename=None, force=False, cache=True):
    """Get a url, optionally with caching
    TODO get headers, use last modified date (save to disk file as meta data), return it (and other metadata) along with page content
    """
    #filename = filename or 'tmp_file.html'
    filename = filename or os.path.join(cache_dir, hash_url(url))
    ## cache it
    if force or not os.path.exists(filename):
        log.debug('getting web page %r', url)
        # TODO grab header information
        # TODO error reporting?

        use_requests = False
        if use_requests:
            response = requests.get(url)
            page = response.text.encode('utf8')  # FIXME revisit this - cache encoding
        else:
            headers = MOZILLA_FIREFOX_HEADERS

            try:
                page = urllib_get_url(url, headers=headers)
            except HTTPError:
                # check for 404?
                page = b''  # wikpedie return data, but we probabl dont want it . E.g. http://eechcentral.simhq.com//index.php?title=Special:Contributions/Arneh returns 404 with page links
                #return nothing so won't look further

        if cache:
            f = open(filename, 'wb')
            f.write(page)
            f.close()
            # initial index - needs reworking - if filename passed in, hash is not used
            index_filename = os.path.join(os.path.dirname(filename), 'index.tsv')
            f = open(index_filename, 'ab')
            entry = '%s\t%s\n' % (os.path.basename(filename), url)
            f.write(entry.encode('utf-8'))
            f.close()
            # TODO log hash and original url to an index of some kind (sqlite3 db probably best)
    else:
        log.debug('getting cached file %r', filename)
        f = open(filename, 'rb')
        page = f.read()
        f.close()
    log.debug('page %d bytes', len(page))  # TODO human bytes
    return page







urls = {}  # dict of urls to scanned_or_not bool

def do_one(url, base_url):
    """
    response = requests.get(
        url=url,
    )
    soup = BeautifulSoup(response.content, 'html.parser')
    """
    page_content = get_url(url)
    if not page_content:
        return False

    soup = BeautifulSoup(page_content, 'html.parser')
    """
    if not soup:
        return False
    """

    # Get all the links
    all_links = soup.find(id="bodyContent").find_all("a")
    #print(all_links)

    new_links_found = False
    for link in all_links:
        #print(type(link), str(link), repr(link))
        #import pdb; pdb.set_trace()
        #print(link.attrs['href'])
        #href = link.attrs['href']
        href = link.attrs.get('href')
        if not href:
            continue
        usable_link = False
        if href.startswith('http'):
            usable_link = True
        elif href.startswith('/') or href.startswith('.'):
            usable_link = True
            href = base_url + href
        else:
            print('ignoring %r' % href)

        if usable_link:
            if 'title=Special:AllPages' in href:
                # avoid a lot of spam - FIXME TODO find a way to go through all pages and only dum p without scan
                continue
            if '?title=AA' in href:
                # probably spam - this maynot be a good huerstic
                continue
            if '?title=AB' in href:
                # probably spam - this maynot be a good huerstic
                continue
            if '?title=AARP' in href:
                # probably spam - this maynot be a good huerstic
                continue
            if '?title=AAA' in href:
                # probably spam - this maynot be a good huerstic
                continue
            if '?title=0' in href:
                # probably spam - this maynot be a good huerstic
                continue
            if '?title=1' in href:
                # probably spam - this maynot be a good huerstic
                continue
            if '?title=2' in href:
                # probably spam - this maynot be a good huerstic
                continue
            if '?title=3' in href:
                # probably spam - this maynot be a good huerstic
                continue
            if '?title=4' in href:
                # probably spam - this maynot be a good huerstic
                continue
            if '?title=5' in href:
                # probably spam - this maynot be a good huerstic
                continue
            if '?title=6' in href:
                # probably spam - this maynot be a good huerstic
                continue
            if '?title=7' in href:
                # probably spam - this maynot be a good huerstic
                continue
            if '?title=8' in href:
                # probably spam - this maynot be a good huerstic
                continue
            if '?title=9' in href:
                # probably spam - this maynot be a good huerstic
                continue
            if '?title=Special:' in href:  # likely to link to spam
                continue
            if '?title=User:' in href:  # likely to link to spam
                continue
            if '&diff=' in href:
                continue
            if '&action=' in href:  # edit and history seen so far
                href = href[:href.find('&action=')]
            if '&oldid=' in href:
                # terribe assumption, assume last paramter
                href = href[:href.find('&oldid=')]
            if '&redirect=no' in href:
                # terribe assumption, assume last paramter
                href = href[:href.find('&redirect=no')]
            if href not in urls:
                # Assume unique, and that extra &/? variables are not being added (or order changed)
                # This assumption is incorrect/flawed/incorrect with respect to oldid parameter (at least...)
                # redirect=no
                # TODO filter out edit - &action=edit
                # modify url to remove redirect=no
                # modify url to remove oldid
                urls[href] = False
                new_links_found = True
    urls[url] = True
    return new_links_found
    

# TODO can I make use of:
#   * http://eechcentral.simhq.com//index.php?title=Special:AllPages
#   * http://eechcentral.simhq.com/index.php?title=Special:AllPages&from=10+Facts+About+Railroad+Cancer+That+Will+Instantly+Bring+You+To+A+Happy+Mood
#   .... loop on
# All pages | Previous page (007 100 GGKING23) | Next page (10 Q
# 
base_url = 'http://eechcentral.simhq.com/'
url = 'http://eechcentral.simhq.com/index.php?title=Engine_startup'
url = 'http://eechcentral.simhq.com/index.php?title=Engine_startup&printable=yes' # appears to be older version of MediaWiki
urls[url] = False
url_count = 0
loop_count = 0
while True:
    try:
        new_links_found = False
        loop_count += 1
        for url in list(urls.keys()):
            url_lower = url.lower()
            if url_lower.endswith('.gif') or url_lower.endswith('.jpeg') or url_lower.endswith('.jpg') or url_lower.endswith('.png'):
                # this does't work when oldid param present
                continue
            if 'eechcentral.simhq.com' not in url_lower:
                continue
            if not urls[url]:
                url_count += 1
                print(url_count)
                new_links_found = new_links_found or do_one(url, base_url=base_url)
        #import pdb; pdb.set_trace()
        if not new_links_found:
            print('no new_links_found')
            break
        if loop_count >= 1000:
            print('loop_count reached')
            break
        """
        if url_count >= 2:
            break
        """
    except KeyboardInterrupt:
        # ctrl-c
        print('search cancelled')
        break
#print(json.dumps(urls, indent=4))
print(url_count)
print(len(urls))
print(loop_count)
f = open('eech_wiki_links.json', 'wb')
f.write(json.dumps(urls, indent=4).encode('utf-8'))
f.close()

