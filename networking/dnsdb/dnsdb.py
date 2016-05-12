#!/usr/bin/env python2.7

## Requires following external modules
##
## ipaddr       https://pypi.python.org/pypi/ipaddr/
## tldextract   https://pypi.python.org/pypi/tldextract/
## curlwrapper  Custom module in 'modules' directory
##   - See module for dependencies

import argparse
import csv
from datetime import datetime
import ipaddr
import json
import re
import site
import sys
import tldextract

site.addsitedir('./modules')
from curlwrapper import CurlWrapper

## DNSDB API stuff
dnsdb_api_key = 'YOUR_API_KEY'
dnsdb_base_url = 'https://api.dnsdb.info'

dnsdb_base_rdata_path = "/lookup/rdata"
dnsdb_base_rrset_path = "/lookup/rrset"
headers = ['X-API-Key: {0}'.format(dnsdb_api_key), 'Accept: application/json']


## Handler for DNSDB queries. The return value is structured as JSON 
## with the following keys:
##
## 'data'	=> the data associated with the subject queried
## 'error'	=> an error string describing any error condition
##
def get_dnsdb_data(subject=None, path=dnsdb_base_rdata_path, args=None):
    ## Default return value
    data = dict(error='No subject')

    try:
        ## Determine if we have an IP or a Name
        rdata_type = 'ip'

        try:
            ipaddr.IPv4Address(subject)
        except ipaddr.AddressValueError:
            rdata_type = 'name'

        ## Construct the DNSDB API path
        url = "{0}{1}".format(dnsdb_base_url, "{0}/{1}/{2}".format(path, rdata_type, subject))

        c = CurlWrapper()
        ret_data = c.get("{0}?limit={1:d}".format(url, args.limit), headers=headers)
        c.reset_cookies()

        ## The API will return nothing if the name or IP is not found
        if not ret_data:
            ## Try again with an rrset query or bail if we already did
            if path != dnsdb_base_rrset_path:
                return get_dnsdb_data(subject, path=dnsdb_base_rrset_path, args=args)

            data['data'] = ret_data
            data['error'] = "No information on %s" % subject
        else:
            ## Process the returned JSON data
            data['data'] = [json.loads(s) for s in ret_data.strip().split("\n")]
            data['error'] = None

    except Exception, e:
        data['error'] = "%s: %s" % (e.__class__.__name__, str(e))

    return json.dumps(data)


if __name__ == "__main__":
    ## Parse options
    arg_parser = argparse.ArgumentParser()

    ## Don't output a CSV header line
    arg_parser.add_argument(
        "--no-header",
        action="store_true",
        default=False,
        help="don't output CSV header"
    )

    ## Print out JSON instead of CSV format
    arg_parser.add_argument(
        "--output-json",
        action="store_true",
        default=False,
        help="output data as JSON"
    )

    ## Output datetimes as ints (CSV only)
    arg_parser.add_argument(
        "--output-datetime-ints",
        action="store_true",
        default=False,
        help="output datetimes as ints (CSV only)"
    )

    ## Output multiple rdata values as separate rows (CSV only)
    arg_parser.add_argument(
        "--output-rdata-as-rows",
        action="store_true",
        default=False,
        help="output rdata values as separate rows (CSV only)"
    )

    ## Filter CSV data based on TLD
    arg_parser.add_argument(
        "--filter-tld",
        help="Only display output that matches TLDs"
    )

    ## Provide a limit on how many records to return
    arg_parser.add_argument(
        "--limit",
        default=10000,
        type=int,
        help="How many records to return; default is 10,000"
    )

    (args, params) = arg_parser.parse_known_args()

    ## Store filters for TLDs
    tld_filter = []
    if args.filter_tld:
        args.filter_tld = re.sub('[\s\.]+', '', args.filter_tld)
        tld_filter = args.filter_tld.split(',');


    ## Determine if we are processing items from the command line or
    ## if something was piped into us from another program.
    data = []
    if not sys.stdin.isatty():
        data = [s.strip() for s in sys.stdin.readlines()]

    else:
        if len(sys.argv) > 1:
            data = [s.strip() for s in params]

    ## Set up CSV items
    csv_writer = csv.writer(sys.stdout, quoting=csv.QUOTE_ALL)
    output_header = args.no_header

    ## Loop through inputs
    for subject in data:
        ## Request DNSDB data
        json_data = get_dnsdb_data(subject.strip(), args=args)

        ## Output JSON data as it's returned
        if args.output_json:
            print json_data
            sys.exit()

        ## Format JSON data into CSV
        json_data = json.loads(json_data)

        ## If we received an error, skip this entry
        if json_data["error"] is not None: continue

        ## Service does not always return the answer in a JSON array
        ## so force all of them into an array.
        if not json_data.get('data'):
            json_data = {'data': [json_data]}

        ## Loop each item and output the data as CSV
        for item in json_data['data']:
            count = item.get('count') or '?'

            bailiwick = item.get('bailiwick')
            rrtype = item.get('rrtype')
            rrname = item.get('rrname')
            rdata = item.get('rdata')

            ## Force all rdata to a list
            if not isinstance(rdata, list):
                rdata = [rdata]

            ## Get domain from rrname; it is output in own field
            (sub, domain, tld) = tldextract.extract(rrname)

            ## Apply TLD filter if one was specified
            if len(tld_filter) > 0 and tld not in tld_filter:
                continue

            domain = "{0}.{1}".format(domain, tld)

            ## Stringify rdata if we aren't outputting it as separate rows
            if not args.output_rdata_as_rows:
                rdata = ", ".join(rdata)

            ## Format all times from UTC timestamp to human-readable format
            time_first = item.get('time_first')
            zone_time_first = item.get('zone_time_first')

            time_last = item.get('time_last')
            zone_time_last = item.get('zone_time_last')

            if time_first is not None:
                if args.output_datetime_ints:
                    dt_first = time_first
                    dt_last = time_last
                    dt_diff = datetime.utcfromtimestamp(dt_last) - datetime.utcfromtimestamp(dt_first)

                else:
                    dt_first = datetime.strptime(str(datetime.utcfromtimestamp(time_first)), "%Y-%m-%d %H:%M:%S")
                    dt_last = datetime.strptime(str(datetime.utcfromtimestamp(time_last)), "%Y-%m-%d %H:%M:%S")
                    dt_diff = dt_last - dt_first

            else:
                if args.output_datetime_ints:
                    dt_first = 0
                    dt_last = 0

                else:
                    dt_first = ""
                    dt_last = ""

                dt_diff = ""

            if zone_time_first is not None:
                if args.output_datetime_ints:
                    dt_zfirst = zone_time_first
                    dt_zlast = zone_time_last
                    dt_zdiff = datetime.utcfromtimestamp(dt_zlast) - datetime.utcfromtimestamp(dt_zfirst)

                else:
                    dt_zfirst = datetime.strptime(str(datetime.utcfromtimestamp(zone_time_first)), "%Y-%m-%d %H:%M:%S")
                    dt_zlast = datetime.strptime(str(datetime.utcfromtimestamp(zone_time_last)), "%Y-%m-%d %H:%M:%S")
                    dt_zdiff = dt_zlast - dt_zfirst

            else:
                if args.output_datetime_ints:
                    dt_zfirst = 0
                    dt_zlast = 0

                else:
                    dt_zfirst = ""
                    dt_zlast = ""

                dt_zdiff = ""

            ## Check if we are writing CSV header
            if output_header is False:
                csv_writer.writerow(["bailiwick", "rrname", "domain", "rrtype", "rdata", "first_seen", "last_seen",
                    "times_seen", "length_seen", "zone_first_seen", "zone_last_seen", "zone_length_seen"])

                output_header = True

            ## Write CSV row
            if not args.output_rdata_as_rows:
                csv_writer.writerow([bailiwick, rrname, domain, rrtype, rdata, str(dt_first), str(dt_last), count,
                    str(dt_diff), str(dt_zfirst), str(dt_zlast), str(dt_zdiff)])

            else:
                for r in rdata:
                    csv_writer.writerow([bailiwick, rrname, domain, rrtype, r, str(dt_first), str(dt_last), count,
                        str(dt_diff), str(dt_zfirst), str(dt_zlast), str(dt_zdiff)])


