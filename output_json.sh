## Send in kv pairs as KEY1 VALUE1 KEY2 VALUE2 ...
function output_json()
{
    local json="{"
    local count=1
    for i in "$@"; do
        if [ $((count % 2)) -eq 0 ]; then
            ## values
            json="${json}\"$i\""
        else
            ## keys
            if [ $count -gt 1 ]; then
                json="${json},\"$i\":"
            else
                json="${json}\"$i\":"
            fi
        fi

        count=$((count + 1))
    done
    json="$json}"

    echo $json
}

