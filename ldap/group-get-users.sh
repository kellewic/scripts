#!/bin/bash

getopt -T > /dev/null
if [[ $? -ne 4 ]]; then
    echo "Required getopt (enhanced) not found"
    exit 1
fi

USER=""
MYGROUPS=()

OPTIONS=""
LONGOPTIONS=group:,user:

PARSED=$(getopt --options=$OPTIONS --longoptions=$LONGOPTIONS --name "$0" -- "$@")
if [[ $? -ne 0 ]]; then
    exit 2
fi

eval set -- "$PARSED"

while true; do
    case "$1" in
        --group)
            MYGROUPS+=("$2")
            shift 2
            ;;
        --user)
            USER="$2"
            shift 2
            ;;
        --)
            shift
            break
            ;;
        *)
            echo "Programming error"
            exit 3
            ;;
    esac
done

BASE_BIND="DC=ads,DC=xxxxx,DC=com"
USER_FILTER="(|(&(samaccounttype=805306368)(!(userAccountControl:1.2.840.113556.1.4.803:=2))(USER))(&(objectCategory=Group)(USER)))"
GROUP_FILTER="(&(objectCategory=Group)(cn=GROUP))"

for GROUP in "${MYGROUPS[@]}"; do
    while IFS= read -r line; do
        #echo "./ld.sh --user=$USER -b \"$BASE_BIND\" --filter=\"${USER_FILTER//USER/$line}\" -q 1 | grep -Ei \"(samaccountname|objectCategory)\" | sed 's/sAMAccountName: *//g' | paste -s -d'~' | sed -r 's/^(.*?)~objectCategory: CN=(\w+),.*/\1 \2/'"

        OUTPUT=()
        mapfile -t OUTPUT < <(./ld.sh --user=$USER -b "$BASE_BIND" --filter="${USER_FILTER//USER/$line}" -q 1 | grep -Ei "(samaccountname|objectCategory):" | sed 's/sAMAccountName: *//g' | paste -s -d'~' | sed -r 's/^(.*?)~objectCategory: CN=(\w+),.*/\1\n\2/')

        if [ "${OUTPUT[1]}" == "Group" ]; then
            ./group-get-users.sh --user=$USER --group="${OUTPUT[0]}"
        else
            if [ ! -z "${OUTPUT[0]}" ]; then
                echo ${OUTPUT[0]}
            fi
        fi
    done < <(./ld.sh --user=$USER -b "$BASE_BIND" --filter="${GROUP_FILTER/GROUP/$GROUP}" -q 1 member | grep -i 'member:' |sed 's/member: *//' | cut -d',' -f1)
done

