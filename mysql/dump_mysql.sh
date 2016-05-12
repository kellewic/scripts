#!/bin/bash
PATH="/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin"
## Backs up MySQL databases to a remote server. Originally written to
## backup a large database of spam data to a NAS.

## Information for host to sync to
SYNC_TO_HOST="your_own.host.here"

## MySQL information of database to sync from
DB_HOST='localhost'
DB_USER='db-user'
DB_PASS='db-pass'

## SSH information used for SYNC_TO_HOST
SSH_USER="root"
SSH_KEY="/root/.ssh/id_rsa"

RSYNC="$(which rsync)"
SSH="$(which ssh)"
MYSQL="$(which mysql)"
MYSQLDUMP="$(which mysqldump)"
PARALLEL="$(which parallel)"
PIGZ="$(which pigz)"

DUMP_DIR='/data/db_dump'
LOCK_FILE="/tmp/$(basename $0).lock"
SYNC_TO_DIR="/data/backup/$(hostname)/mysql/"
RSYNC_OPTS="-a --no-g --no-o --remove-source-files"

## Where to log messages
LOG_FILE="/var/log/$(basename $0 .sh).log"

## Reset log file
rm -f "$LOG_FILE"


## Function to write a log message
function write_log()
{
	## Only echo if there is a message
	if [ ! -z "$1" ]; then
		## Get the date to add to the log entry
		local date="[$(date +"%Y-%m-%d %H:%M:%S"),$(date +"%N" | sed 's/^\([0-9][0-9][0-9]\).*/\1/') $(date +"%z")]"

		## Goes to log file and stdout
		echo "$date: $*" | tee -a $LOG_FILE
	fi
}

write_log "---------- START $(date) ----------"

[ ! -x "$RSYNC" ] && write_log "Cannot execute $RSYNC" && exit 1
[ ! -x "$SSH" ] && write_log "Cannot execute $SSH" && exit 1
[ ! -x "$MYSQL" ] && write_log "Cannot execute $MYSQL" && exit 1
[ ! -x "$MYSQLDUMP" ] && write_log "Cannot execute $MYSQLDUMP" && exit 1
[ ! -x "$PARALLEL" ] && write_log "Cannot execute $PARALLEL" && exit 1
[ ! -x "$PIGZ" ] && write_log "Cannot execute $PIGZ" && exit 1
[ -e "$LOCK_FILE" ] && write_log "Lock file exists ($LOCK_FILE); cannot run" && exit 2
[ ! -d "$DUMP_DIR" ] && mkdir -m770 -p "$DUMP_DIR"

touch $LOCK_FILE
rm -f $DUMP_DIR/*.gz

## Make directory for rsync if it doesn't exist
$SSH -i $SSH_KEY -l $SSH_USER $SYNC_TO_HOST "mkdir -p $SYNC_TO_DIR"

## Remove files on NAS older than 'keep_days' days except for spam_ and spam_messages_ files
## which are only backed up once.
keep_days="+14"
$SSH -i $SSH_KEY -l $SSH_USER $SYNC_TO_HOST "find $SYNC_TO_DIR -type f -regex .*.gz -mtime $keep_days -print | grep -Ev 'spam_20|spam_messages_20' | xargs rm -fv"

suf="$(date +'%Y%m%d').sql"
last_day="$(date -d '1 day ago' +'%Y%m%d')"

function on_exit()
{
	rm -f $LOCK_FILE
	write_log "---------- STOP  $(date) ----------"
}
trap on_exit EXIT


## Main backup block
for DB_DB in $($MYSQL -B -b -h $DB_HOST -u $DB_USER --password=$DB_PASS -e "SHOW DATABASES" | \
	grep -Ev "Database|information_schema|performance_schema"); do

	## These two variables control how many tables to back up in a run. This is so if the database hasn't
	## been backed up in a while, we don't run the disk out of space dumping the database for backup. Setting
	## both to -1 will perform a backup of all tables that need it.
	skip=-1
	keep=-1

	## Make DB directory for rsync if it doesn't exist
	SYNC_TO_DB_DIR="${SYNC_TO_DIR}${DB_DB}"
	$SSH -i $SSH_KEY -l $SSH_USER $SYNC_TO_HOST "mkdir -p $SYNC_TO_DB_DIR"

	## Uncomment to skip specific databases for testing
	#[ "$DB_DB" == "db1" ] && continue
	#[ "$DB_DB" == "db2" ] && continue
	#[ "$DB_DB" == "db3" ] && continue

	write_log "DATABASE(${DB_DB})"
	write_log "SKIP($skip)"
	write_log "KEEP($keep)"

	tmp_file=$(mktemp)

	for table in $($MYSQL -B -b -h $DB_HOST -u $DB_USER --password=$DB_PASS -e "SHOW TABLES FROM $DB_DB" | \
		grep -iv "tables_in_"); do

		## Skip specific tables we don't need backed up in the mysql database
		if [ "$DB_DB" == "mysql" ]; then
			for t in slow_log general_log ndb_binlog_index 'help_*' 'time_zone_*'; do
				if echo "$table" | grep -E "$t" &>/dev/null; then
					continue 2
				fi
			done
		fi

		if [ $skip -ne -1 -a $keep -ne -1 ]; then
			## Skip some number of tables to backup
			if [ $skip -gt 0 ]; then
				write_log "SKIP($table; $skip)"
				skip=$((skip - 1))
				continue
			fi

			## If we have reached the limit of tables to back up, skip the rest
			if [ $keep -eq 0 ]; then
				write_log "SKIP($table); K0"
				continue
			fi

			## Only keep some number of tables for backup
			if [ $keep -gt 0 ]; then
				keep=$((keep - 1))
			fi
		fi

		## Set initial date far in the past so tables get included
		table_date="20000101"

		## Check spam_YYYY-MM-DD and spam_messages-YYYY-MM-DD to see if 
		## they are newer than yesterday so we don't back up partial tables
		## Past tables will be included in the exclude files to signify we
		## have already backed them up.
		if [ "${table:0:6}" == "spam_2" ]; then
			table_date="${table:5:4}${table:10:2}${table:13:2}"
		elif [ "${table:0:13}" == "spam_messages" ]; then
			table_date="${table:14:4}${table:19:2}${table:22:2}"
		fi

		## Skip new tables that are likely still being written to
		if [ $table_date -gt $last_day ]; then
			write_log "IN_USE($table)"
			continue
		fi

		## Check if we have already dumped and backed this table up
		if [ "$DB_DB" == "spam" ] && [ "${table:0:6}" == "spam_2" -o "${table:0:13}" == "spam_messages" ]; then
			## Only keep one backup of spam_ and spam_messages_ tables in the spam database. They do not 
			## change once the day has rolled over.
			ret=$($SSH -i $SSH_KEY -l $SSH_USER $SYNC_TO_HOST "ls $SYNC_TO_DB_DIR/${DB_DB}.${table}.*.gz" 2>&1)
		else
			ret=$($SSH -i $SSH_KEY -l $SSH_USER $SYNC_TO_HOST "ls $SYNC_TO_DB_DIR/${DB_DB}.${table}.${suf}.gz" 2>&1)
		fi

		if ! echo "$ret" | grep -i "No such file" &>/dev/null; then
			write_log "ON_NAS($SYNC_TO_DB_DIR/${DB_DB}.${table}.${suf}.gz)"
			continue
		fi

		if [ "$DB_DB" == "spam" ] && [ "${table:0:6}" == "spam_2" -o "${table:0:13}" == "spam_messages" ]; then
			## Check count on table to see if it's being modified
			count1=$($MYSQL -B -b -h $DB_HOST -u $DB_USER --password=$DB_PASS -e "SELECT COUNT(*) FROM $DB_DB.\`$table\`" | grep -v "COUNT")
			sleep 5
			count2=$($MYSQL -B -b -h $DB_HOST -u $DB_USER --password=$DB_PASS -e "SELECT COUNT(*) FROM $DB_DB.\`$table\`" | grep -v "COUNT")

			if [ $count1 -ne $count2 ]; then
				write_log "IN_USE($table); $count1/$count2"
				continue
			fi
		fi

		write_log "BACKUP($table)"

		## Save table to file for backup processing
		echo $table >> $tmp_file
	done

	if [ $(stat --printf="%s" $tmp_file) -eq 0 ]; then
		write_log "NO BACKUPS NEEDED"
		continue
	fi

	## Dump tables in parallel and gzip them
	cat $tmp_file | $PARALLEL -j 3 "(echo [$(date +'%Y-%m-%d %H:%M:%S'),$(date +'%N' | sed 's/^\([0-9][0-9][0-9]\).*/\1/') $(date +'%z')]: \
		DUMP\({}\) | tee -a $LOG_FILE) && $MYSQLDUMP -h $DB_HOST -u $DB_USER --password=$DB_PASS \
		--allow-keywords -c -F -q --add-drop-table --add-locks --create-options --extended-insert \
		--flush-privileges --max_allowed_packet=128M $DB_DB {} > $DUMP_DIR/${DB_DB}.{}.$suf && $PIGZ -p 2 $DUMP_DIR/${DB_DB}.{}.$suf"

	for file in `ls $DUMP_DIR/*.gz 2>&-`; do
		write_log "RSYNC($file)"
		## Transfer files to the backup server
		$RSYNC -h --out-format='[%t]: %o %n (%b)' $RSYNC_OPTS -e "$SSH -i $SSH_KEY -l $SSH_USER" $file $SYNC_TO_HOST:$SYNC_TO_DB_DIR | tee -a $LOG_FILE
	done
done
