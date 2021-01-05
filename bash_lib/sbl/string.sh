_sbl_string=1

## Strip off all matching characters from the left side of string; defaults to spaces
##
## $1   - String to work with
## $2   - Character to remove
function string_lstrip()
{
    shopt -q -s extglob
    echo "${1##+(${2:- })}"
}

## Strip off all matching characters from the right side of string; defaults to spaces
##
## $1   - String to work with
## $2   - Characters to remove
function string_rstrip()
{
    shopt -q -s extglob
    echo "${1%%+(${2:- })}"
}

## Strip off all matching characters from the left and right sides of string; defaults to spaces
##
## $1   - String to work with
## $2   - Characters to remove
function string_strip()
{
    echo "$(string_rstrip "$(string_lstrip "$1" "$2")" "$2")"
}

