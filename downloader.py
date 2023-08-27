
from eechcentral_wiki_scraper import  *

f = open('eech_wiki_links.json', 'rb')
json_bytes = f.read()
f.close()
urls = json.loads(json_bytes.decode('utf-8'))

for url in urls:
    if 'simhq.' in url:
        page_content = get_url(url)  # don't do anything with it, just get it cached
        # TODO if a file type (e.g. gif, png, jpg, jpeg, pdf, etc.) scrape for urls
        #   1. a href link
        #   2. img (thumb?)
