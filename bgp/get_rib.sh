#!/bin/bash
PATH="/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin"

WGET="$(which wget)"
CURL="$(which curl)"
PYTHON="$(which python)"

## Local base directory for app
BASE_RUN_DIR="/root"

## Script to convert the BGP data to something we can grep
CONVERT_RIB="$BASE_RUN_DIR/convert_rib.py"

## Store converted BGP data to this file
IP_ASN_DAT="$BASE_RUN_DIR/ipasndat"

## URL to retrieve latest BGP data
BGP_DATA_URL="http://archive.routeviews.org/bgpdata/$(date -u +'%Y.%m')/RIBS"

## Function to write a log message
function write_log()
{
	## Only echo if there is a message
	if [ ! -z "$1" ]; then
		## Get the date to add to the log entry
		local date="[$(date +"%Y-%m-%d %H:%M:%S"),$(date +"%N" | sed 's/^\([0-9][0-9][0-9]\).*/\1/') $(date +"%z")]"

		## Goes to log file and stdout
		echo "$date: $*"
	fi
}

write_log "------------------- Start run -------------------"

## Check that we can execute needed binaries
[ ! -x "$WGET" ] && write_log "Cannot execute $WGET" && exit 1
[ ! -x "$CURL" ] && write_log "Cannot execute $CURL" && exit 1
[ ! -x "$PYTHON" ] && write_log "Cannot execute $PYTHON" && exit 1
[ ! -d $BASE_RUN_DIR ] && write_log "$BASE_RUN_DIR does not exist!" && exit 1
[ ! -e "$CONVERT_RIB" ] && write_log "Cannot find $CONVERT_RIB" && exit 1

## Get the latest RIB file chock-full of BGP data
write_log "Checking MRT RIB files"
BGP_DOWNLOAD_FILE=$($WGET -q -O - $BGP_DATA_URL | grep 'rib\..*\.bz2' | sed 's/^.*>\(rib.*\.bz2\).*/\1/' | tail -n 1)
BGP_LOCAL_FILE="$BASE_RUN_DIR/$BGP_DOWNLOAD_FILE"
write_log "   Newest RIB file is $BGP_DOWNLOAD_FILE"

if [ ! -e "$BGP_LOCAL_FILE" ]; then
	## Check to make sure we can access the file. Sometimes a 403 Forbidden is returned
	## if the file is there, but not fully written to disk on the remote side.
	write_log "   Checking availability of $BGP_DOWNLOAD_FILE"

	while true; do
		if $CURL -iI $BGP_DATA_URL/$BGP_DOWNLOAD_FILE 2>/dev/null | grep Forbidden 2&>/dev/null; then
			write_log "      Not available"
			sleep 3
		else
			write_log "      Available"
			break
		fi
	done

	write_log "   Downloading $BGP_DATA_URL/$BGP_DOWNLOAD_FILE"
	$WGET -P $BASE_RUN_DIR $BGP_DATA_URL/$BGP_DOWNLOAD_FILE

	## Remove the old ASN file
	rm -f $IP_ASN_DAT
fi

## Additional check just for logging purposes; keep processing with current data
[ ! -e $BGP_LOCAL_FILE ] && write_log "   Failed to download $BGP_DATA_URL/$BGP_FILE" && exit 2

## Remove old RIB files
for i in `ls $BASE_RUN_DIR/rib.*.bz2 2>&- | grep -v $BGP_DOWNLOAD_FILE`; do
	write_log "   Removing $i"
	rm -f "$i" 
done

## Make sure we have converted BGP data
if [ ! -e $IP_ASN_DAT ]; then
	## Convert the newest RIB file to something human-readable
	write_log "   Running MRT RIB log importer"
	$PYTHON $CONVERT_RIB $BGP_LOCAL_FILE $IP_ASN_DAT
fi

write_log "------------------- End run -------------------"
