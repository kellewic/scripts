#!/usr/bin/python

## Decode P2B v3 format
## https://sourceforge.net/p/peerguardian/wiki/dev-blocklist-format-p2b/

import binascii
import os.path
import struct
import sys

data = sys.argv[1]

if os.path.isfile(data):
    with open(data, 'rb') as fd:
        data = fd.read().strip()

names = []
name_ranges = {}

x = 0
header = data[x:x+7]

if header == '\xFF\xFF\xFF\xFFP2B':
    x += 7
    version = int(ord(data[x:x+1]))
    x += 1

    print "P2B file, version %d" % version

    namecount, = struct.unpack("!I", data[x:x+4])
    x += 4

    print "%d names" % namecount

    s = ''
    while True:
        c = data[x:x+1]
        x += 1
        
        if c == '\x00':
            names.append(s)
            #print s
            s = ''

            if (len(names) == namecount):
                break
        else:
            s += c

    rangecount, = struct.unpack("!I", data[x:x+4])
    x += 4

    print "%d ranges" % rangecount

    while rangecount > 0:
        nameindex, start, end = struct.unpack("!III", data[x:x+12])
        x += 12

        start_ip = ".".join(map(lambda n: str(start>>n & 0xFF), [24,16,8,0]))
        end_ip = ".".join(map(lambda n: str(end>>n & 0xFF), [24,16,8,0]))

        print "%s: %s, %s" % (names[nameindex], start_ip, end_ip)

        name = names[nameindex]

        if name not in name_ranges:
            name_ranges[name] = []

        name_ranges[name].append([start, end])

        rangecount -= 1

