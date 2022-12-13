#!/usr/bin/env python3
#-*- coding: utf-8 -*-

from elasticsearch import Elasticsearch
import os, sys, json, requests, getpass, getopt


#### Accept arguments ####
args=sys.argv[1:]
ifile = ''
trange = '7' # Default date range is 7 days
fname = 'fts' # Full text search is default

try:
    opts, args = getopt.getopt(args,"hi:r:f:")
except getopt.GetoptError:
   print ('ioc-digger.py -i <filename-with-ioc> -r <range-number-of-days> -f <field-name-to-search>')
   print ('ioc-digger.py: default days is 7 and default search is full text search')
   sys.exit(2)

for opt, arg in opts:
   if opt == '-h':
      print ('ioc-digger.py -i <filename-with-ioc> -r <range-number-of-days> -f <field-name-to-search>')
      print ('ioc-digger.py: default days is 7 and default search is full text search')
      sys.exit()
   elif opt in ("-i"):
      ifile = arg
   elif opt in ("-r"):
      trange = arg
   elif opt in ("-f"):
      fname = arg

#### === ####

### Set the date range in days ###

trange = "now-" + trange + "d"

#### === ####


### Check if the indicators file exist ###

if not os.path.isfile(ifile):
    print("ioc-digger.py: Cannot find indicator file ", ifile,)
    print ('ioc-digger.py -i <filename-with-ioc> -r <range-number-of-days> -f <field-name-to-search>')
    print ('ioc-digger.py: default days is 7 and default search is full text search')
    sys.exit()

#### === ####


## Specify the Elasticsearch Cluster
elasticsearch_nodes = [
    "https://es1:9200",
    "https://es2:9201",
]


elastic_user = input("Elastic Username: ")
elastic_password = getpass.getpass('Elastic Password:')

# create a client instance of Elasticsearch
elastic_client = Elasticsearch(
        elasticsearch_nodes,
        ca_certs="/opt/certs/elastic/ca.crt",
        basic_auth=(elastic_user, elastic_password)
)

result_list = {} #python dict to hold the results, just like perl hashes
print_header = 0 #do not print matched header unless something is found
with open(ifile,'r') as fp:
        for index, line in enumerate(fp):
            indicator = format(line.strip())

            if fname == "fts":
                print ("ioc-digger.py: INFO: performing full text search for: ", indicator)
                response = elastic_client.search(index="logs-*", terminate_after=1, size="0", query={ "bool": { "must": [], "filter": [ { "multi_match": { "type": "phrase", "query": indicator, "lenient": "true" } }, { "range": { "@timestamp": { "format": "strict_date_optional_time", "gte": trange, "lte": "now" }}}],"should": [], "must_not": [] }})
                result_list[indicator] = response['hits']['total']['value']
            else: 
                print ("ioc-digger.py: INFO: searching ", fname, "for: ", indicator)
                response = elastic_client.search(index="logs-*", terminate_after=1, size="0", query={ "bool": { "must": [], "filter": [ { "bool": { "should": [ { "match_phrase": { fname: indicator }} ], "minimum_should_match": 1 }}, { "range": { "@timestamp": { "format": "strict_date_optional_time", "gte": trange, "lte": "now" }}} ], "should": [], "must_not": [] }})
                result_list[indicator] = response['hits']['total']['value']

### Time to show the results if any ###
print_header = 0
for key, value in result_list.items():
    if value > 0:
        print_header +=1
        print("\nioc-digger.py: CRITICAL: The following indicators were found in the logs:") if print_header == 1 else None
        print(key)

print("\nioc-digger.py: INFO: No indicator matches found ") if print_header == 0 else None
