'''
    Copyright 2018 Fedor Chervyakov

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
'''
import requests
from requests.exceptions import HTTPError, ReadTimeout
from lxml import etree

import itertools
import re
import sys
import logging

_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logging.basicConfig(level=logging.INFO, format=_format)

logger = logging.getLogger(__name__)

sitemap_pattern = re.compile('sitemap: ([\w.\:\-/]+\.xml/?)', re.IGNORECASE)
crawl_delay_pattern = re.compile('crawl\-delay: ([\d.]+)', re.IGNORECASE)

xml_namespaces = {'sitemap' : "http://www.sitemaps.org/schemas/sitemap/0.9"}

def get_robots(url):
    ''' 
    Retrieves robots.txt from
    url + /robots.txt
    '''
    # Building link to robots.txt
    if url[-1] != '/': url += '/'
    robots_url = url + 'robots.txt'

    logger.info('Fetching robots.txt from {0}'.format(robots_url))
    # Fetching robots.txt
    try:
        timeout = 15
        r = requests.get(robots_url,timeout=timeout)
        r.raise_for_status()
        logger.debug(r.text)
        return r.text
    except HTTPError as e:
        logger.error('Request for {0} FAILED with code {1}'
                    .format(robots_url,r.status_code))
        raise e
    except ReadTimeout as rt:
        logger.error('Request for {0} TIMEOUTed after {1} seconds.'
                    .format(robots_url,timeout))
        raise rt
    except Exception as ex:
        logger.exception(ex)
        raise ex

def parse_robots(robots_string,crawl_delay=True):
    ''' 
    Parse robots.txt for sitemap entries
    and if crawl_delay flag is True 
    fetch value for crawl-delay
    '''
    params = dict()
    # Reading sitemap entries
    matches = sitemap_pattern.findall(robots_string)
    params['sitemaps'] = set(matches)
    
    if crawl_delay:
        # Reading crawl-delay
        c = crawl_delay_pattern.search(robots_string)
        if c: params['crawl-delay'] = c.group(1)
        
    return params

def parse_sitemap(sitemap_url):
    '''
    Fetching links from specified sitemap
    '''
    # Fetching sitemap from sitemap_url
    logger.info('Requesting {0}'.format(sitemap_url))
    try:
        r = requests.get(sitemap_url)
        r.raise_for_status()
    except HTTPError as h:
        logger.error('Request for {0} FAILED with status code {1}'
                    .format(sitemap_url,r.status_code))
        raise h
    
    root = etree.fromstring(r.content)
    if 'sitemapindex' in root.tag:
        # Requested page is sitemapindex
        logger.info('   Looks like this is sitemapindex.')
        # Fetching urlsets from this sitemapindex
        sitemaps = [c.findtext('sitemap:loc',namespaces=xml_namespaces) 
                    for c in root.getchildren()]
        logger.info('   Sitemaps in this index: {0}'.format(sitemaps))
        # Fetching links from each urlset
        links_multid = [parse_sitemap(s) for s in sitemaps]
        # Flattenning multidimensional list of links
        links = list(itertools.chain(links_multid)) 
    elif 'urlset' in root.tag:
        # Requested page is urlset
        logger.info('   This looks like urlset.')
        # Fetching links from this urlset
        links = [c.findtext('sitemap:loc', namespaces=xml_namespaces)
                for c in root.getchildren()]
        logger.info('   Succesfully fetched {0} links from {1}'
                    .format(len(links),sitemap_url))

    return links

def main():
    '''
    Used only for developement and debugging purposes
    '''
    for arg in sys.argv[1:]:
        url = arg
        robots = get_robots(url)
        params = parse_robots(robots)
        logger.info(params)
        for sitemap in params['sitemaps']:
            links = parse_sitemap(sitemap)

if __name__ == '__main__':
    main()