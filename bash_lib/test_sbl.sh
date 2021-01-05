#!/bin/bash

## Load up the libraries. Can be called as any of:
## load_libary sbl/date
## load_library date
## load_library date sbl/log net sbl/string
. "$(dirname $0)/sbl/lib.sh"
load_library date log
load_library sbl/net
load_library string


date_to_stamp "%Y-%m-%d %H:%M:%S" "2011-12-14 00:00:00"

log_write "To stdout"

inet_aton 127.0.0.1
inet_ntoa 2130706433

string_lstrip "...   Help   ..." .
string_rstrip "...   Help   ..." .
string_strip  "...   Help   ..." .

## TODO: Lockfile routines
##
## lockfile_create - register an on_exit command to remove it if specified
##		lockfile_create [dir] [template] [remove_on_exit flag]
##			dir defaults to TMPDIR, if dir is specified cache TMPDIR, replace it, restore it
##			template defaults to XXXX
##			remove_on_exit flag defaults to on
##		returns name of file created
##
##

