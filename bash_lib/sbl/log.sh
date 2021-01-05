_sbl_log=1

##
## $1   - Files to send logs to (comma-separated); if not present logs are sent to stdout
## $2*  - Log message
##
function log_write()
{
    local log_files_IN="$1" && shift
    local msg="$*"

    local IN

    ## Don't output to stdout by default
    local do_stdout="0"

    ## Log files to send output to
    declare -a log_files

    ## Gather up all the log files given
    while IFS="," read -ra IN; do
        for i in "${IN[@]}"; do
            ## Strip spaces from start and end of string
            i="${i## }"
            i="${i%% }"

            if [ "$i" == "stdout" ]; then
                do_stdout="1"
            else
                log_files[${#log_files[*]}]="$i"
            fi
        done
    done <<< "$log_files_IN"

    ## Make sure log file exist
    for log_file in "${log_files[@]}"; do
        if [ ! -e "$log_file" ]; then
            ## If a log file doesn't exist, the entire operation fails
            ## and we assume this is part of the message. All
            ## output is sent to stdout instead.
            msg="${log_files[@]} ${msg}"
            log_files=()
            do_stdout="1"
            break
        fi
    done

    ## Make sure we have a message
    if [ ${#msg} -gt 0 ]; then
        ## Get the date to add to the log entry
        local date="[$(date +"%Y-%m-%d %H:%M:%S"),$(date +"%N" | sed 's/^\([0-9][0-9][0-9]\).*/\1/') $(date +"%z")]"

        if [ "$do_stdout" == "0" ]; then
            echo "$date: $msg" | tee -a "${log_files[@]}" >/dev/null
        else
            echo "$date: $msg" | tee -a "${log_files[@]}"
        fi
    fi
}


