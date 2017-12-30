# zillow_scraps


## Describtion
Script will store info about rental/for sale apparments in local MongoDB. DB data will be valid for a week. After a week, upon  next script run, old results will be deleted.
Script allows to query Zillow according to a postal code or list of postal codes. Query either *rentals* or appartments for *sale* (default)

## Requirements

1. zestimate API is fetched for appartments for sale. In order to use this feature - clone the repo and put the script in the created directory
https://github.com/seme0021/python-zillow

2. Script uses this repo as a base (I've re-wrote the script below according to my needs)
https://gist.github.com/scrapehero/5f51f344d68cf2c022eb2d23a2f1cf95

You might want to register and get your API key. 

3. Uses local MongoDB to cache results 

See demo at http://35.156.108.83/

