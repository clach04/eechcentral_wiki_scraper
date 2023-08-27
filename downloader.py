
from eechcentral_wiki_scraper import  *

f = open('eech_wiki_links.json', 'rb')
json_bytes = f.read()
f.close()
urls = json.loads(json_bytes.decode('utf-8'))

for url in urls:
    if 'simhq.' in url:
        page_content = get_url(url)  # don't do anything with it, just get it cached
