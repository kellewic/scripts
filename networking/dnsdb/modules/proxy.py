from base64 import b64encode
import re
import sys

class Proxy(object):
   _proxy_url = None
   _proxy_port = None
   _proxy_user = None
   _proxy_pass = None


   def __init__(self, **kwargs):
      self.proxy_url = kwargs.get('proxy_url', None) or self._proxy_url
      self.proxy_port = kwargs.get('proxy_port', None) or self._proxy_port
      self.proxy_user = kwargs.get('proxy_username', None) or self._proxy_user
      self.proxy_pass = kwargs.get('proxy_password', None) or self._proxy_pass

      auth = ''
      scheme = ''
      url = ''

      if self.proxy_user and self.proxy_pass:
         auth = "{0}:{1}".format(self.proxy_user, self.proxy_pass)
         self.proxy_auth = b64encode(auth)
         self.proxy_auth_header = {'Proxy-Authorization': 'Basic {0}'.format(self.proxy_auth)}

      if self.proxy_url and self.proxy_url.startswith('http'):
         m = re.match('(https?://)(.*)', self.proxy_url)

         if m:
            scheme, url = m.groups()

      self.proxies = {
         'http': "{0}{1}:{2}".format(scheme, url, self.proxy_port),
         'https': "{0}{1}:{2}".format(scheme, url, self.proxy_port)
      }


   def __str__(self):
      return str(self.__dict__)



def main(*args):
   print Proxy()
   return 0


if __name__ == '__main__':
   sys.exit(main(*sys.argv))

