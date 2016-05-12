#!/bin/env python2.7
"""
-------------------------------------------------------------------------------
| REQUIREMENTS
-------------------------------------------------------------------------------
* pwhois.org access (Free; no registration - queries limited per day by IP)
* Python 2.7+ (not tested with 3.x)
* dnspython
* requests

-------------------------------------------------------------------------------
| USAGE
-------------------------------------------------------------------------------
This script is run by passing URLs, domains, and IPs as parameters; the same
input can also be sent via UNIX pipe.

python script.py [-h|--help]

python script.py --field IP --field Hostname --field NS --quote-none 1.2.3.4

-- OR --

cat domains.txt | python script.py --field Input --field IP --quote-none

-------------------------------------------------------------------------------
| OUTPUT
-------------------------------------------------------------------------------
The output is CSV with the following fields (in this order by default):

IP                      Determined IP
Prefix                  Prefix for IP
City                    City geo-location for IP
Region                  Region geo-location for IP
Country                 Country name geo-location for IP
Country-Code            Country code geo-location for IP
Latitude                Latitude geo-location for IP
Longitude               Longitude geo-location for IP
Net-Range               Network range IP exists in
Net-Name                Network name at RIR
Net-Name-Source         RIR network name came from
Net-Type                How network was assigned to org
Net-Register-Date       When network was registered
Net-Update-Date         When network was last updated
Net-Create-Date         First time seen?
Net-Modify-Date         Last time modified?
Can-Allocate            Can org sub-allocate this network?
Next-Hop                Next hop past IP?
Origin-AS               ASN for IP
AS-Path                 AS path
AS-Org-Name             Org name for ASN
AS-Org-Name-Source      Source of AS data
Route-Create-Date       First time seen?
Route-Modify-Date       Last time modified?
Input                   Original input processed
Hostname                Determined hostname
CNAMES                  Determined CNAMEs (comma-separated list)
NS                      Determined nameservers (comma-separated list)
Scheme                  Scheme portion of Input
URL-Path                Path portion of Input
Ping                    IP responds to pings (Y/N)
Web                     HTTP status code of HEAD check
Org-Name                Name of org at RIR
Org-Name-Source         RIR org pulled from
Org-Record              Org record number?
Org-ID                  ID for org at RIR
Street-1                Street for org
Org-City                City for org
State                   State/Region for org
Postal-Code             Postal code for org
Org-Country             Country for org
Register-Date           Date org registered at RIR
Update-Date             Last org record change at RIR
Abuse-Handle            Abuse handle at RIR
Abuse-Phone             Abuse phone according to RIR
Abuse-Email             Abuse email according to RIR
NOC-Handle              NOC handle at RIR
NOC-Phone               NOC phone according to RIR
NOC-Email               NOC email according to RIR
Tech-Handle             Tech handle at RIR
Tech-Phone              Tech phone according to RIR
Tech-Email              Tech email according to RIR
Admin-Handle            Admin handle at RIR
Admin-Phone             Admin phone according to RIR
Admin-Email             Admin email according to RIR
Create-Date             When first created at pwhois.org
Modify-Date             When last modified at pwhois.org
Cache-Date              When last cached at pwhois.org

The script tries not to fault regardless of errors and will place empty
strings in the output fields when no answer is available for any reason.
"""

import argparse
import csv
from datetime import datetime
import dns.resolver
import dns.reversename
import itertools
import json
import re
import requests
import signal
import socket
import subprocess
import sys
import urllib2


## Basic Exception representing a timeout
class TimeoutException(Exception):
    def __init__(self, ivalue=""):
        self.value = ivalue

    def __str__(self):
        return repr(self.value)


## Wrap up alarm functionality since dns.resolver.timeout doesn't seem to work
class Alarm:
    def __init__(self, timeouthandler=None, timeout=2592000):
        if not timeouthandler:
            timeouthandler = self._timeout_handler

        self.old_sigalarm = None
        self.timeout = timeout
        self.timeouthandler = timeouthandler

    def _timeout_handler(self, s, f):
        raise TimeoutException("{0} second timeout exceeded".format(self.timeout))

    def set(self, seconds=None):
        self.old_sigalarm = signal.signal(signal.SIGALRM, self.timeouthandler)

        if seconds is not None:
            self.timeout = seconds

        signal.alarm(self.timeout)

    def clear(self):
        signal.alarm(0)
        signal.signal(signal.SIGALRM, self.old_sigalarm)


## Various date formats returned from pwhois.org
date_formats = {
    "Route-Create-Date": "%b %d %Y %H:%M:%S",
    "Route-Modify-Date": "%b %d %Y %H:%M:%S",
    "Net-Create-Date": "%b %d %Y %H:%M:%S",
    "Net-Modify-Date": "%b %d %Y %H:%M:%S",
    "Create-Date": "%b %d %Y %H:%M:%S",
    "Modify-Date": "%b %d %Y %H:%M:%S",
    "Net-Register-Date": "%Y-%m-%d",
    "Net-Update-Date": "%Y-%m-%d",
    "Register-Date": "%Y-%m-%d",
    "Update-Date": "%Y-%m-%d",
}

## Go with ISO 8601 to standardize the above dates
common_date_format = "%Y-%m-%dT%H:%M:%SZ"

## Get additional data from pwhois.org
def get_pwhois(ip):
    whois = {"Error": ""}

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(("whois.pwhois.org", 43))
        s.send("type=all {0}\n".format(ip))
        data = ""

        while True:
            data_str = s.recv(4096)
            if not data_str: break
            data += data_str

        data = data.strip()
        s.close()

        ## Happens when we exceed our daily query limit
        if re.search("Error: Unable to perform lookup", data):
            whois["Error"] = data

    except Exception, e:
        whois["Error"] = str(e)

    if len(whois["Error"]) == 0:
        for l in data.split("\n"):
            (k, v) = l.split(":", 1)
            (k, v) = (k.strip(), v.strip())

            if k in date_formats:
                v = datetime.strptime(v, date_formats[k]).isoformat()

            ## A few items have the same label, but they are returned in
            ## the same order every time so we can adjust them.
            if k == 'Country' and k in whois:
                k = 'Org-Country'

            elif k == 'City' and k in whois:
                k = 'Org-City'

            whois[k] = v

        if "Cache-Date" in whois:
            ts = datetime.utcfromtimestamp(int(whois["Cache-Date"]))
            whois["Cache-Date"] = ts.isoformat()

    return whois


## DNS query
def dns_query(resolver, subject, qtype):
    alarm = Alarm()
    answers = []

    if qtype == "PTR":
        subject = dns.reversename.from_address(subject)

    try:
        alarm.set(dns_resolver.timeout)
        dns_answer = resolver.query(subject, qtype, raise_on_no_answer=False)

        if (dns_answer.response.flags & dns.flags.TC) == dns.flags.TC:
            dns_answer = resolver.query(subject, qtype, tcp=True)

    except:
        dns_answer = None

    finally:
        alarm.clear()

    try:
        ## Some DNS servers return NXDOMAIN as part of TXT
        if not re.search(".*?TXT.*?not\s+exist", str(dns_answer.response)):
            answers = [str(a) for a in dns_answer]
    except:
        pass

    return answers


## Very basic check for what looks like an IP
def is_ip(ip=""):
    return re.match("^(?:\d+\.){3}\d+$", ip)


## Main
if __name__ == "__main__":
    ## Output fields in the order we want them to appear
    data_keys = [
        "IP", "Prefix", "City", "Region", "Country", "Country-Code",
        "Latitude", "Longitude",

        "Net-Range", "Net-Name", "Net-Name-Source", "Net-Type",
        "Net-Register-Date", "Net-Update-Date","Net-Create-Date", 
        "Net-Modify-Date", "Can-Allocate", "Next-Hop",

        "Origin-AS", "AS-Path", "AS-Org-Name", "AS-Org-Name-Source",
        "Route-Create-Date", "Route-Modify-Date",

        "Input", "Hostname", "CNAMES", "NS", "Scheme", "URL-Path",
        "Ping", "Web",

        "Org-Name", "Org-Name-Source", "Org-Record", "Org-ID", "Street-1",
        "Org-City", "State", "Postal-Code", "Org-Country", "Register-Date",
        "Update-Date",

        "Abuse-Handle", "Abuse-Phone", "Abuse-Email",
        "NOC-Handle", "NOC-Phone", "NOC-Email",
        "Tech-Handle", "Tech-Phone", "Tech-Email",
        "Admin-Handle", "Admin-Phone", "Admin-Email",

        "Create-Date", "Modify-Date", "Cache-Date"
    ]

    ## Parse options
    arg_parser = argparse.ArgumentParser()

    ## Don't output a CSV header line
    arg_parser.add_argument(
        "--no-header",
        action="store_true",
        default=False,
        help="don't output CSV header"
    )

    ## Only quote fields with special characters; this doesn't quote 
    ## fields with spaces
    arg_parser.add_argument(
        "--quote-minimal",
        dest="csv_quoting",
        action="store_const",
        const=csv.QUOTE_MINIMAL,
        default=csv.QUOTE_ALL,
        help="only quote CSV fields with special characters"
    )

    ## Don't quote any fields
    arg_parser.add_argument(
        "--quote-none",
        dest="csv_quoting",
        action="store_const",
        const=csv.QUOTE_NONE,
        default=csv.QUOTE_ALL,
        help="don't quote any CSV fields"
    )

    ## Multi-value field separator used when a field contains more than
    ## one value. When quoting is on (default), this is a ', ' string. If
    ## quoting is changed via --quote-xxx then this is changed to'|' unless
    ## already specified on the command-line.
    arg_parser.add_argument(
        "--value-sep",
        default=", ",
        type=str,
        metavar="SEPARATOR",
        help="string to use as a separator for multi-value columns"
    )

    ## Try to reach IP via ICMP echo
    arg_parser.add_argument(
        "--ping",
        action="store_true",
        default=False,
        help="run ping test"
    )

    ## Try to reach URL/Domain via HTTP(S)
    arg_parser.add_argument(
        "--web",
        action="store_true",
        default=False,
        help="rub web test"
    )

    ## Timeout in seconds to use for DNS queries
    arg_parser.add_argument(
        "--dns-timeout",
        default=1,
        type=int,
        metavar="SECS",
        help="timeout for DNS queries"
    )

    ## List of DNS servers to use for queries; specified using multiple flags
    arg_parser.add_argument(
        "--dns-server",
        dest="dns_servers",
        action="append",
        default=[],
        metavar="IP",
        help="DNS server to use for queries; can use multiple times"
    )

    ## The CSV fields to output; will be printed in order given
    arg_parser.add_argument(
        "--field",
        dest="fields",
        action="append",
        default=[],
        metavar="CSV_FIELD",
        help="CSV field to output; can use multiple times; fields are in order"
    )

    ## The CSV fields not to output; will override --fields flags regardless of
    ## command-line positioning.
    arg_parser.add_argument(
        "--no-field",
        dest="nofields",
        action="append",
        default=[],
        metavar="CSV_FIELD",
        help="CSV field not to output; can use multiple times; overrides --field"
    )

    (args, params) = arg_parser.parse_known_args()

    ## If quoting has been changed
    if args.csv_quoting != csv.QUOTE_ALL:
        ## and the multi-value field separator has not changed
        if args.value_sep == ', ':
            ## Change it to be more non-quote friendly
            args.value_sep = '|'

    ## If no fields were specified, use all of them as a default
    if len(args.fields) == 0:
        args.fields = data_keys

    ## Ensure we have valid CSV field values
    args.nofields = list(
        itertools.ifilter(lambda f: data_keys.count(f)>0, args.nofields)
    )

    ## Ensure we have valid CSV field values
    args.fields = list(
        itertools.ifilter(lambda f: data_keys.count(f)>0, args.fields)
    )

    ## Remove nofields values from fields list
    args.fields = list(
        itertools.ifilter(lambda f: args.nofields.count(f)==0, args.fields)
    )

    ## Use Google nameservers by default since they don't seem to pull
    ## any NXDOMAIN redirection bullshit.
    args.dns_servers.extend(["8.8.8.8", "8.8.4.4"])

    ## Set up our DNS resolver
    dns_resolver = dns.resolver.Resolver(configure=True)
    dns_resolver.nameservers = args.dns_servers

    ## No negative DNS timeouts allowed
    if args.dns_timeout <= 0:
        dns_resolver.timeout = 1
    else:
        dns_resolver.timeout = args.dns_timeout

    ## Set up our CSV writer
    csv_writer = csv.writer(sys.stdout, quoting=args.csv_quoting)

    ## Accept input piped in as well as passed in
    data = []
    if not sys.stdin.isatty():
        data = [s.strip() for s in sys.stdin.readlines()]

    else:
        if len(params) > 0:
            data = [s.strip() for s in params]

    ## Write CSV header if necessary
    if args.no_header == False and len(data) > 0:
        csv_writer.writerow(args.fields)

    ## Check out what we got as input
    for subject in data:
        (scheme, path) = ("", "")
        original_subject = subject
        subject_type = "DOMAIN"

        ## Check for scheme, save it, and remove it from subject
        m = re.match("^h...s?://", subject)
        if m is not None:
            scheme = m.group(0)
            subject = re.sub(scheme, "", subject)
            scheme = re.sub("h..p", "http", scheme)

        ## Check for path, save it, and remove it from subject
        m = re.search("/.*$", subject)
        if m is not None:
            path = m.group(0)
            subject = re.sub(path, "", subject)
            subject_type = "URL"

            ## Save a default scheme if not present
            if len(scheme) == 0:
                scheme = "http://"

        ## What's left?
        if is_ip(subject):
            subject_type = "IP"


        ## Get hostname, IPs, and CNAMEs
        try:
            if subject_type == "IP":
                ips = [subject]
                hostname = dns_query(dns_resolver, subject, "PTR")[0]

            else:
                hostname = subject
                ips = dns_query(dns_resolver, subject, "A")

            cnames = dns_query(dns_resolver, hostname, "CNAME")
            nameservers = dns_query(dns_resolver, hostname, "NS")

        except Exception, e:
            ## Something went wrong, go with the basics
            cnames = []
            nameservers = []

            if subject_type == "IP":
                ips = [subject]
                hostname = ""

            else:
                ips = []
                hostname = subject

        ## Process all IPs we have
        for ip in ips:
            w = get_pwhois(ip)
            [w.setdefault(k, "") for k in data_keys]

            #if len(w["Error"]) > 0:
                ## Happens when we exceed our daily query limit; give all
                ## default fields empty string values.
            #    [w.setdefault(k, "") for k in data_keys]

            w["IP"] = ip
            w["Input"] = original_subject
            w["Scheme"] = scheme
            w["URL-Path"] = path
            w["Hostname"] = hostname
            w["CNAMES"] = args.value_sep.join(cnames)
            w["NS"] = args.value_sep.join(nameservers)
            w["Web"] = ""
            w["Ping"] = ""

            ## Quick and dirty web test
            if args.web is True and len(scheme) > 0:
                try:
                    r = requests.head("{0}{1}{2}".format(scheme, subject, path))
                    w["Web"] = r.status_code
                except:
                    pass


            ## Is IP ICMP reachable?
            if args.ping is True and len(w["IP"]) > 0:
                try:
                    p1 = subprocess.Popen(
                            ["ping", "-n", "-c", "1", "-W", "1", "-q", w["IP"]],
                            stdout=subprocess.PIPE
                    )

                    p2 = subprocess.Popen(
                            ["grep", "100% packet loss"],
                            stdin=p1.stdout,
                            stdout=subprocess.PIPE
                    )

                    p1.stdout.close()

                    output = p2.communicate()[0]

                    if len(output) == 0:
                        w["Ping"] = "Y"
                    else:
                        w["Ping"] = "N"

                except:
                    pass


            csv_writer.writerow([w[k] for k in args.fields])

