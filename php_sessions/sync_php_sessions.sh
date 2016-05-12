#!/bin/env bash
PATH="/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin"

RSYNC="$(which rsync)"
SSH="$(which ssh)"
CHOWN="$(which chown)"
SSH_KEY="/home/user/.ssh/id_rsa"
SSH_USER="user"
SYNC_TO_HOST="host2"
SYNC_DIR="/www/sessions"
OWNER="apache"
GROUP="apache"
LOG_FILE="/var/log/$(basename $0 .sh).log"

HOSTNAME="$(hostname)"
if [ ${HOSTNAME:0:11} == "host2" ]; then
        SYNC_TO_HOST="host1"
fi

$(which inotifywait) -mr --format '%:e %w %f' -e close_write -e delete $SYNC_DIR | \
while read e dir file; do
        date="[$(date +"%Y-%m-%d %H:%M:%S"),$(date +"%N" | sed 's/^\([0-9][0-9][0-9]\).*/\1/') $(date +"%z")]"
        SYNC_FILE="${dir}${file}"

        echo "$date: ${e}($SYNC_FILE)" | tee -a $LOG_FILE

        if [ -e "$SYNC_FILE" ]; then
                (echo -n "${date}: LOCAL " && \
                        $CHOWN -v ${OWNER}.$GROUP "$SYNC_FILE" && chmod 660 "$SYNC_FILE") | tee -a $LOG_FILE

                ($RSYNC --out-format="$date: %o %n (%b)" -au -e "$SSH -i $SSH_KEY -l $SSH_USER" $SYNC_FILE $SYNC_TO_HOST:$SYNC_FILE | tee -a $LOG_FILE) && \
                        (echo -n "${date}: REMOTE " && $SSH -i $SSH_KEY -l $SSH_USER $SYNC_TO_HOST "sudo $CHOWN -v ${OWNER}.$GROUP $SYNC_FILE") | tee -a $LOG_FILE
        else   
                ret=$($SSH -i $SSH_KEY -l $SSH_USER $SYNC_TO_HOST "sudo rm -vf $SYNC_FILE")
                [ ! -z "$ret" ] && echo "$date: REMOTE $ret" | tee -a $LOG_FILE

                ## Remove empty session files that monitoring tools tend to leave
                $(which find) "$dir" -type f -regex .*sess_.* -empty -delete
                $SSH -i $SSH_KEY -l $SSH_USER $SYNC_TO_HOST "sudo find $dir -type f -regex .*sess_.* -empty -delete"
        fi
done
