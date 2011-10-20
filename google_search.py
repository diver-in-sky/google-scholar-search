import httplib
import urllib
import urlparse
from BeautifulSoup import BeautifulSoup
import re
import time
import hashlib
import os

class GoogleScholarSearch:
    def __init__(self):
        self.SEARCH_HOST = "scholar.google.com"
        self.SEARCH_BASE_URL = "/scholar"

    def get_page_fields(self, html):
        results = []
        # Screen-scrape the result to obtain the publication information
        soup = BeautifulSoup(html)
        for record in soup('div', {'class': 'gs_r'}):
            # Includeds error checking
            topPart = record.first('h3')                                
                    
            # get article url
            pubURL = ""
            if topPart.a:
                pubURL = topPart.a['href']
                # Clean up the URL, make sure it does not contain '\' but '/' instead
                pubURL = pubURL.replace('\\', '/')
                
            # get download pdf url
            downloadPart = record.first('span')
            downloadURL = ""
            if downloadPart.a:
                downloadURL = downloadPart.a['href']
                # Clean up the URL, make sure it does not contain '\' but '/' instead
                downloadURL = downloadURL.replace('\\', '/')

            pubTitle = ""
            if topPart.a:
                for part in topPart.a.contents:
                    pubTitle += str(part.string)

            if pubTitle == "":
                pubTitle = topPart.text.strip()
               
            authorPart = record.first('span', {'class': 'gs_a'}).string
            if authorPart == None:
                authorPart = re.search('<span class="gs_a">(.*?)</span>',str(record)).group(1)
            num = authorPart.count(" - ")
            # Assume that the fields are delimited by ' - ', the first entry will be the
            # list of authors, the last entry is the journal URL, anything in between
            # should be the journal year
            idx_start = authorPart.find(' - ')
            idx_end = authorPart.rfind(' - ')
            pubAuthors = authorPart[:idx_start]             
            tmpSearch = re.search('\d{4}',authorPart[idx_start + 3:idx_end])
            pubJournalYear = ''
            if tmpSearch:
                pubJournalYear = tmpSearch.group(0)
            pubJournalURL = authorPart[idx_end + 3:]
            # If (only one ' - ' is found) and (the end bit contains '\d\d\d\d')
            # then the last bit is journal year instead of journal URL
            if pubJournalYear=='' and re.search('\d\d\d\d', pubJournalURL)!=None:
                pubJournalYear = pubJournalURL
                pubJournalURL = ''
                               
            # This can potentially fail if all of the abstract can be contained in the space
            # provided such that no '...' is found
            delimiter = soup.firstText("...")
            if delimiter:
                delimiter = delimiter.parent
            pubAbstract = ""
            while delimiter and str(delimiter)!='Null' and (str(delimiter)!='<b>...</b>' or pubAbstract==""):
                pubAbstract += str(delimiter)
                delimiter = delimiter.nextSibling
                
            match = re.search("Cited by ([^<]*)", str(record))
            pubCitation = ''
            if match != None:
                pubCitation = match.group(1)
            results.append({
                    "URL": pubURL,
                    "DOWNLOAD_URL": downloadURL,
                    "Title": pubTitle,
                    "Authors": pubAuthors,
                    "JournalYear": pubJournalYear,
                    "JournalURL": pubJournalURL,
                    "Abstract": pubAbstract,
                    "NumCited": pubCitation,
                    })
        return results

    # example
    # http://scholar.google.com/scholar?hl=en&q=&as_publication=sigir&btnG=Search&as_sdt=0%2C5&as_ylo=2009&as_yhi=2011&as_vis=0
    def advanced_search_publication(self, as_publication, from_year, to_year, start=0, limit=10):
        results = []
        
        while start+10<=limit:
            last_results = len(results)
            params = urllib.urlencode({'q': "", 'as_ylo': from_year, 'as_yhi': to_year, 'start': start,
                                       'as_publication': as_publication, 'hl': 'en', 'btnG': 'Search'})
            headers = {'User-Agent': 'Mozilla/4.0 (compatible; MSIE 5.5; Windows NT)'}
            url = self.SEARCH_BASE_URL+"?"+params
            conn = httplib.HTTPConnection(self.SEARCH_HOST)
            conn.request("GET", url, {}, headers)
            resp = conn.getresponse()      
            if resp.status==200:
                html = resp.read()
                html = html.decode('ascii', 'ignore')
                results.extend(self.get_page_fields(html))
            else:
                print "ERROR: ",
                print resp.status, resp.reason
                return []
            start+=10
            if (len(results) - last_results) == 0:
                print "no additional results. break"
                break
            print start
            time.sleep(3)
        return results
        
    def search_tearms(self, terms, limit=10):
        start = 0
        results = []
        while start+10<=limit:
            params = urllib.urlencode({'q': "+".join(terms),'as_yhi': 2008, 'start': start })
            headers = {'User-Agent': 'Mozilla/4.0 (compatible; MSIE 5.5; Windows NT)'}

            url = self.SEARCH_BASE_URL+"?"+params
            conn = httplib.HTTPConnection(self.SEARCH_HOST)
            conn.request("GET", url, {}, headers)
    
            resp = conn.getresponse()      
            if resp.status==200:
                html = resp.read()
                html = html.decode('ascii', 'ignore')
                results.extend(self.get_page_fields(html))
            else:
                print "ERROR: ",
                print resp.status, resp.reason
                return []
            start+=10
            print start
            time.sleep(3)
        return results

if __name__ == '__main__':
    search = GoogleScholarSearch()
    pubs = search.advanced_search_publication('sigir', 2009, 2011, 0, 2000)
    for pub in pubs:
        print pub['Title']
        print pub['Authors']
        print pub['JournalYear']
        print pub['JournalURL']
        print pub['Abstract']
        print pub['NumCited']
        print pub['URL']
        print pub['DOWNLOAD_URL']
        
        if pub['DOWNLOAD_URL']:
            md5hex_filename = hashlib.md5(pub['DOWNLOAD_URL']).hexdigest()[:8]
            file_exists = os.path.isfile(md5hex_filename+".txt")
            print "md5 hex: %s" % md5hex_filename
            
            if not file_exists:
                ftxt = open(md5hex_filename+".txt", "w")
                for key, item in pub.iteritems():
                    ftxt.write("%s: %s\n" % (key, item))
                ftxt.close()
                
                print "downloading... %s" % pub['DOWNLOAD_URL']
                url = urlparse.urlparse(pub['DOWNLOAD_URL'])
                if url.port:
                    conn = httplib.HTTPConnection(url.hostname, url.port)
                else:
                    conn = httplib.HTTPConnection(url.hostname)
                headers = {'User-Agent': 'Mozilla/4.0 (compatible; MSIE 5.5; Windows NT)'}
                conn.request("GET", url.path+"?"+url.query, {}, headers)
                resp = conn.getresponse()
                if resp.status==200:
                    data = resp.read()
                    fpdf = open(md5hex_filename+".pdf", "wb")
                    fpdf.write(data)
                    fpdf.close()
                else:
                    print "ERROR during download pdf url"
            else:
                print "file with md5 %s already exists" % md5hex_filename

        print "======================================"
