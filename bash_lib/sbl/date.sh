_sbl_date=1

function date_to_stamp()
{
    ## Assume the first arg is a date format string
    local format="$1"
    shift
    local date_str="$*"

    if [ -z "$date_str" ]; then
        date_str="$format"
    fi

    local date=$(date -u -d "$date_str" +%s 2>&-)

    if [ -z "$date" ]; then
        date=$(date -ju -f "$format" "$date_str" +%s 2>&-)
    fi

    echo $date
}
