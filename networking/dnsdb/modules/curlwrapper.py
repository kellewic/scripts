## General wrapper around pycurl that sets up redirects, cookies, proxy,
## authentication, SSL certs, etc.
##
## pycurl options references:
##    http://curl.haxx.se/c/curl_easy_setopt.html
##    https://github.com/blackstonetech/pycurl/blob/master/src/pycurl.c
##
## pycurl2 - https://pypi.python.org/pypi/pycurl2/7.20.0.a1
##    pip install -U pycurl2
##       *requires libcurl-devel
##
## proxy is custom module with no outside dependencies

import cStringIO
import os
import pycurl
import sys

from proxy import Proxy
from tempfile import mkstemp
from urllib import urlencode


class CurlWrapper(object):
   ## Attributes recognized by __init__ with defaults set
   proxy_url = None
   proxy_port = None
   proxy_username = None
   proxy_password = None

   ## Assumes PEM format with private key embedded
   ssl_cert_filename = None
   ssl_key_password = None

   ## HTTP auth username and password
   http_username = None
   http_password = None

   ## User-agent pycurl will use
   user_agent = 'Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 6.1; Trident/4.0)'

   ## Set to validate SSL certificates
   ssl_verify = True

   ## Set to use cookies
   use_cookies = True

   ## Set to false to stop automatic urlencoding
   auto_urlencode = True

   ## Set to cause pycurl to be verbose
   verbose = False


   def __init__(self, **kwargs):
      ## Get proxy settings
      proxy = Proxy(**kwargs)

      ## Adjust kwargs
      kwargs['proxy_url'] = proxy.proxy_url or kwargs.get('proxy_url')
      kwargs['proxy_port'] = proxy.proxy_port or kwargs.get('proxy_port')
      kwargs['proxy_username'] = proxy.proxy_user or kwargs.get('proxy_username')
      kwargs['proxy_password'] = proxy.proxy_pass or kwargs.get('proxy_password')

      ## Dynamically add properties to class instance
      for k, v in kwargs.iteritems():
         self.__setattr__(k, v)

      ## Set up cookie properties
      self.reset_cookies()


   ## For easy viewing of what properties are set
   def __str__(self):
      return str(self.__dict__)


   ## Main method used by get() and post()
   def _retrieve(self, url, data=None, data_size=None, headers=None):
      c = pycurl.Curl()

      if self.verbose:
         c.setopt(pycurl.VERBOSE, 1)

      c.setopt(pycurl.URL, url)

      ## Set up some HTTP headers
      if self.user_agent:
         c.setopt(pycurl.USERAGENT, str(self.user_agent))

      ## Set up proxy using Basic auth (default)
      if self.proxy_url:
         c.setopt(pycurl.PROXY, str(self.proxy_url))
         c.setopt(pycurl.PROXYPORT, int(self.proxy_port))
         c.setopt(pycurl.PROXYUSERPWD, "{0!s}:{1!s}".format(self.proxy_username, self.proxy_password))

      ## Set up redirects; follow long enough to get bounced around a bit, 
      ## but avoid infinite loops.
      c.setopt(pycurl.FOLLOWLOCATION, 1)
      c.setopt(pycurl.MAXREDIRS, 20)

      if self.ssl_verify:
         ## Verify all SLL certs in the chain
         c.setopt(pycurl.SSL_VERIFYPEER, 1)
         c.setopt(pycurl.SSL_VERIFYHOST, 2)

      else:
         ## Turn off SSL certificate verification; useful if going through
         ## a host proxy like Burp Suite
         c.setopt(pycurl.SSL_VERIFYPEER, 0)
         c.setopt(pycurl.SSL_VERIFYHOST, 0)

      ## Set options for SSL client certificate
      if self.ssl_cert_filename:
         c.setopt(pycurl.SSLCERT, self.ssl_cert_filename)

      if self.ssl_key_password:
         c.setopt(pycurl.SSLKEYPASSWD, self.ssl_key_password)

      ## Set up HTTP authentication
      if self.http_username and self.http_password:
         c.setopt(pycurl.USERPWD, "{0!s}:{1!s}".format(self.http_username, self.http_password))
         c.setopt(pycurl.HTTPAUTH, pycurl.HTTPAUTH_BASIC)

      ## Set up cookies if needed
      if self.use_cookies:
         ## Set up cookie loading and storage
         if self.cookie_fd is None:
            self.cookie_fd, self.cookie_filename = mkstemp()

         c.setopt(pycurl.COOKIEFILE, self.cookie_filename)
         c.setopt(pycurl.COOKIEJAR, self.cookie_filename)

      ## Are we sending GET or POST?
      if data is None:
         c.setopt(pycurl.HTTPGET, 1)

      else:
         c.setopt(pycurl.POST, 1)

         ## Data to send
         if self.auto_urlencode:
            c.setopt(pycurl.POSTFIELDS, urlencode(data))

         else:
            c.setopt(pycurl.POSTFIELDS, data)

         ## In case of binary files, can provide size manually
         if data_size is not None:
            c.setopt(pycurl.POSTFIELDSIZE_LARGE, data_size)

      if headers is not None:
         c.setopt(pycurl.HTTPHEADER, headers)

      ## Set up buffer to read response
      r = cStringIO.StringIO()
      c.setopt(pycurl.WRITEFUNCTION, r.write)

      ## Send request
      c.perform()

      ## Store response
      data = r.getvalue()

      ## Cleanup
      r.close()
      c.close()

      return data


   def reset_cookies(self):
      if self.use_cookies:
         ## Close cookie file
         try:
            os.close(self.cookie_fd)
         except:
            pass

         ## Delete cookie file
         try:
            os.unlink(self.cookie_filename)
         except:
            pass

         self.cookie_fd = None
         self.cookie_filename = None


   ## Send HTTP GET; query strings should be provided as part of the URL
   def get(self, url, headers=None):
      return self._retrieve(url, headers=headers)


   ## Send HTTP POST
   ## data should be in whatever format the endpoint is expecting (i.e. URL-encoded, etc)
   ## data_size should be set for binary data; if not set then C strlen() is called
   def post(self, url, data=None, data_size=None, headers=None):
      return self._retrieve(url, data=data, data_size=data_size, headers=headers)


def main(*args):
   t = CurlWrapper(
      verbose = True
   )

   print t.get('http://www.google.com')
   t.reset_cookies()

   return 0


if __name__ == '__main__':
   sys.exit(main(*sys.argv))

