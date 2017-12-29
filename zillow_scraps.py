import zillow
from lxml import html
import requests
from pymongo import MongoClient
import argparse
import time
from datetime import datetime  
from datetime import timedelta  

class Zillow(object):
    def __init__(self, sort, codes, key):
        self.key = key
        self.sort = sort
        self.codes = codes
        self.api = zillow.ValuationApi()
        client = MongoClient('localhost', 27017)
        mydb = client.zillow_scraps
        self.zillow_collection = mydb.rentals
        self.zillow_code_date = mydb.rentals_code_date
        if 'rent' != sort:
            self.zillow_collection = mydb.sales
            self.zillow_code_date = mydb.sales_code_date
        self.zestimate_collection = mydb.zestimate
        self.headers= {
            'accept':'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'accept-encoding':'gzip, deflate, sdch, br',
            'accept-language':'en-GB,en;q=0.8,en-US;q=0.6,ml;q=0.4',
            'cache-control':'max-age=0',
            'upgrade-insecure-requests':'1',
            'user-agent':'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36'
        }
    
    def get_zillow_code_date_db(self, code):
        print("get_zillow_code_date_db code:", code)
        doc = self.zillow_code_date.find_one({'code': code})
        if doc != None:
            present = datetime.now()
            print("get_zillow_code_date_db date to check:", doc["date"])
            if doc["date"] + timedelta(days=7) > present:
                return 1
            else:
                print("need to update!")
                self.zillow_code_date.remove ({'code': code}, True)
                return 0
        else:
            print("zillow postal code date doc not found")
            code_date_obj = {
                'code': code,
                'date': datetime.utcnow()
            }
            self.zillow_code_date.insert(code_date_obj)
            return 0

    def get_zestimate_amount_db(self, zpid):
        print("get_zestimate_amount_db zpid:", zpid)
        doc = self.zestimate_collection.find_one({'zpid': zpid})
        if doc != None:
            print(doc["amount"])
        else:
            print("zestimate doc not found")

    def run(self):
        insert_count = 0
        cache_count = 0
        for code in self.codes:    
            self.clean_zillow_old_results(code)
            if self.get_zillow_code_date_db(code) == 1: 
                cache_count += 1
                continue
            scraped_data = self.get_scraped_data(code)
            #print(scraped_data)
            for row in  scraped_data:
                url = row["url"]
                if not self.zillow_collection.find({'url': url}).count() > 0:
                    #print("url doesn't exists in DB:" + url)
                    self.zillow_collection.insert(row)
                    insert_count += 1
            
        print("Inserted to DB:", insert_count, " cache results:", cache_count)

    def getZestimate(self, zpid):
        try:
            #print("getZestimate zpid:", zpid)
            if not self.zestimate_collection.find({'zpid': zpid}).count() > 0:
                detail_data = self.api.GetZEstimate(self.key, zpid)
                amount = detail_data.get_dict()['zestimate']['amount']
                #print("zestimate amount:", amount)
                zestimate_obj = {
                    'zpid': zpid,
                    'amount': amount,
                    'date': datetime.utcnow()
                }
                self.zestimate_collection.insert(zestimate_obj)
                return amount
            else:
                result = self.zestimate_collection.find_one({'zpid': zpid})
                #print("DB zestimate result: ", result['amount']) # it can be None
                return result['amount']
        except:
            zestimate_obj = {
                'zpid': zpid,
                'amount': None,
                'date': datetime.utcnow()
            }
            self.zestimate_collection.insert(zestimate_obj)
            return None
    
    def convert_price_to_int(self, price):
        pricelist = price.split(' ')
        if len(pricelist) > 1:
            price = pricelist[1]
            if '+' in price:
                price = price.split('+')[0]
        if 'K' in price:
            price = price.split('$')[1][:-1]
        elif 'mo' in price:
            price = price.split('$')[1].split('/')[0]
        elif '+' in price:
            price = price.split('+')[0]
        
        if '$' in price:
            price = price.split('$')[1]

        if ',' in price:
            priceparts = price.split(',')
            price = int(''.join(priceparts))
        return price

    def get_zillow_obj(self, properties, postal_code):
        raw_price = properties.xpath(".//span[@class='zsg-photo-card-price']//text()")
        raw_info = properties.xpath(".//span[@class='zsg-photo-card-info']//text()")
        url = properties.xpath(".//a[contains(@class,'overlay-link')]/@href")
        raw_title = properties.xpath(".//h4//text()")
        address = ' '.join(url[0].split('/')[2].split('-')[:-1]) # don't take the postal code
        price = ''.join(raw_price).strip() if raw_price else None
        info = ' '.join(' '.join(raw_info).split()).replace(u"\xb7",',') if raw_info else None
        title = ''.join(raw_title) if raw_title else None
        property_url = "https://www.zillow.com"+url[0] if url else None 
        zpid = properties.xpath("@data-zpid")[0]
        if '.' in zpid:
            zpid = None
        longitude = properties.xpath("@data-longitude")[0]
        latitude = properties.xpath("@data-latitude")[0]
        zestimate = None
        ztype = "rent"
        if 'rent' not in self.sort:
            valz = self.getZestimate(int(zpid))
            zestimate = valz if valz else None
            ztype = "buy"
        if price == None:
            price = self.convert_price_to_int(info)
        else:
            price = self.convert_price_to_int(price)
        #print("get_zillow_obj price:", price)

        zillow_obj = {
            'address': address,
            'postal_code': postal_code,
            'price': price,
            'info': info,
            'url': property_url,
            'zestimate': zestimate,
            'title': title,
            'ztype': ztype,
            "date" : datetime.utcnow(),
            "zpid" : zpid,
            "longitude": longitude,
            "latitude": latitude
        }
        return zillow_obj

    def clean_zillow_old_results(self, code):
        present = datetime.now()
        for doc in self.zillow_collection.find({'postal_code': code}):
            if doc["date"] + timedelta(days=7) > present:
                continue
            else:
                self.zillow_collection.remove({'zpid': doc["zpid"]}, True)

    def get_scraped_data(self, postal_code):
        if self.sort == "rent":
            url = "https://www.zillow.com/homes/for_rent/{0}/0_singlestory/days_sort".format(postal_code)
        else:
            url = "https://www.zillow.com/homes/for_sale/{0}/0_singlestory/days_sort".format(postal_code)
        print("scraping url:", url)

        for i in range(5):
            try:
                response = requests.get(url,headers=self.headers)
                parser = html.fromstring(response.text)
                search_results = parser.xpath("//div[@id='search-results']//article")
                properties_list = []
                for properties in search_results:
                    zillow_obj = self.get_zillow_obj(properties, postal_code)
                    #print('zillow_obj:', zillow_obj)
                    if zillow_obj != None:
                        properties_list.append(zillow_obj)
                #print("properties_list:", properties_list)
                return properties_list
            except:
                print ("Failed to process the page",url)
        
        print("Some error happened, returning None")
        return None

if __name__=="__main__":
    argparser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
    sortorder_help = """
        available sort orders are :
        rent: Latest properties for rent,
        sale: Latest properties for sale
        """
    argparser.add_argument('sort', nargs='?', help = sortorder_help, default ='Homes For You')
    argparser.add_argument('codes', metavar='N', type=int, nargs='+', help='List of postal codes')
    args = argparser.parse_args()
    z = Zillow(args.sort, args.codes, "X1-ZWz18uxxby8tfv_a9fju")
    z.run()