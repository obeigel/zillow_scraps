# zillow_scraps

## Requirements

1. In order to perform zestimate API
https://github.com/seme0021/python-zillow

2. Used as a base code from 
https://gist.github.com/scrapehero/5f51f344d68cf2c022eb2d23a2f1cf95

First, clone python-zillow, and make sure it runs. You might want to register and get your API key.
Then - place this script in same directory and run it.

3. Uses MongoDB to cache results 

## Describtion
Script will store info about rental/for sale apparments in local MongoDB for a week. After a week, and next script run, old results will be deleted
Script allows to query Zillow according to postal code, or list of postal codes. Query either rentals or appartments for sale (default)
