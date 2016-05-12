## API documentation can be found at http://www.team-cymru.org/Services/ip-to-asn.html

from dns.exception import DNSException
import dns.resolver
import re
import socket

origin_asn_zone = 'origin.asn.cymru.com'
desc_asn_zone = 'asn.cymru.com'
whois_server = 'whois.cymru.com'
whois_port = 43
fullbogons_dns = 'v4.fullbogons.cymru.com'

## Determine if IP is in the bogons list and return the prefix
def get_bogon_by_dns(ip, source_ip=None):
	try:
		subject = "%s.%s" % ('.'.join(reversed(ip.split('.'))), fullbogons_dns)

		resolver = dns.resolver.Resolver()
		dns_answer = resolver.query(subject, rdtype=16, source=source_ip)
		return ''.join([str(a) for a in dns_answer]).strip('"')

	except dns.resolver.NXDOMAIN:
		return None

	except DNSException, e:
		raise Exception("%s: %s" % (e.__class__.__name__, e.__doc__))

	except Exception, e:
		error = str(e)
		if not error: error = e.__doc__
		raise Exception("%s: %s" % (e.__class__.__name__, error))


## Get ASN data by using the DNS API
def get_asn_data_by_dns(ip, source_ip=None):
	try:
		subject = "%s.%s" % ('.'.join(reversed(ip.split('.'))), origin_asn_zone)

		resolver = dns.resolver.Resolver()
		dns_answer = resolver.query(subject, rdtype=16, source=source_ip)
		answer = ''.join([str(a) for a in dns_answer])

		asn_str, prefix = [a.strip("\" ") for a in answer.split('|')][:2]
		asns = [a.strip() for a in asn_str.split(' ')]
		ret = []

		for asn in asns:
			subject = "AS%s.%s" % (asn, desc_asn_zone)
			dns_answer = resolver.query(subject, rdtype=16, source=source_ip)
			answer = ''.join([str(a) for a in dns_answer])
			name = [a.strip("\" ") for a in answer.split('|')][-1]
			ret.append([ip, prefix, asn, name])

		return ret

	except dns.resolver.NXDOMAIN:
		return [] 

	except DNSException, e:
		raise Exception("%s: %s" % (e.__class__.__name__, e.__doc__))

	except Exception, e:
		error = str(e)
		if not error: error = e.__doc__
		raise Exception("%s: %s" % (e.__class__.__name__, error))


## Get ASN data by using the whois API
def get_asn_data_by_whois(ip):
	try:
		s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		s.connect((whois_server, whois_port))
		s.send("%s\n" % ip)
		response = ''

		while True:
			d = s.recv(4096)
			if not d: break
			response += d

		s.close()

		response = re.sub("^AS.*?\n", "", response)
		nl_split = response.strip().split("\n")
		ret = []

		for i in nl_split:
			asn, ip, name = [a.strip() for a in i.split('|')]
			if asn == 'NA': asn = 0
			ret.append([ip, '', asn, name])

		return ret

	except Exception, e:
		error = str(e)
		if not error: error = e.__doc__
		raise Exception("%s: %s" % (e.__class__.__name__, error))

