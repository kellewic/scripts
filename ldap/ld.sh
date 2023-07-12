#!/bin/bash

getopt -T > /dev/null
if [[ $? -ne 4 ]]; then
    echo "Required getopt (enhanced) not found"
    exit 1
fi

LDAPSEARCH_CMD="/opt/pbis/bin/ldapsearch"

USER="" ## --user=XXXX
PASS="" ## --pass=XXXX
LDAP="ldap://" ## -H XXXX
BIND="" ## -b XXXX
FILTER="" ## --filter=XXXX
TL="8" ## timelimit, -l ##
SL="5000" ## sizelimit, -z ##
NT="10" ## network timeout, --nt=##
TIME="0" ## flag to time the search, -t [0|1]
QUIET="0" ## flag to reduce output, -q [0|1]

OPTIONS=b:,t:,q:,H:,l:,z:
LONGOPTIONS=filter:,nt:,user:,pass:

PARSED=$(getopt --options=$OPTIONS --longoptions=$LONGOPTIONS --name "$0" -- "$@")
if [[ $? -ne 0 ]]; then
    exit 2
fi
eval set -- "$PARSED"

PASS_FILE=~/".ldp"

function read_pass_from_file()
{
    if [ -e "$PASS_FILE" ]; then
        PASS=$(< <(base64 -d $PASS_FILE))
    fi
}

function read_pass_from_term()
{
    read -r -t 30 -s -p "Enter LDAP password for $USER: " PASS
    echo $PASS|base64 >$PASS_FILE
    chmod 600 $PASS_FILE
}

while true; do
    case "$1" in
        -b)
            BIND="$2"
            shift 2
            ;;
        -H)
            LDAP="$2"
            shift 2
            ;;
        -l)
            TL="$2"
            shift 2
            ;;
        -z)
            SL="$2"
            shift 2
            ;;
        -t)
            TIME="$2"
            shift 2
            ;;
        -q)
            QUIET="$2"
            shift 2
            ;;
        --user)
            USER="$2"
            shift 2
            ;;
        --pass)
            PASS="$2"
            [ -z "$PASS" ] && read_pass_from_file
            [ -z "$PASS" ] && read_pass_from_term
            shift 2
            ;;
        --nt)
            NT="$2"
            shift 2
            ;;
        --filter)
            FILTER="$2"
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

function run_command()
{
    [ -z "$PASS" ] && read_pass_from_file
    [ -z "$PASS" ] && read_pass_from_term

    if [ "$QUIET" == "0" ]; then
        COMMAND="$LDAPSEARCH_CMD -LLL -l $TL -z $SL -o nettimeout=$NT -x -W -H $LDAP -D $USER -b \"$BIND\" \"$FILTER\" $*"
        echo
        echo "RUNNING: $COMMAND"
        echo
    fi

    if [ "$TIME" == "1" ]; then
        time $LDAPSEARCH_CMD -LLL -l $TL -z $SL -o nettimeout=$NT -x -w $PASS -H $LDAP -D $USER -b "$BIND" "$FILTER" $*
    else
        $LDAPSEARCH_CMD -LLL -l $TL -z $SL -o nettimeout=$NT -x -w $PASS -H $LDAP -D $USER -b "$BIND" "$FILTER" $*
    fi
}

run_command
while [ $? == 49 ]; do
    read_pass_from_term
    run_command
done

