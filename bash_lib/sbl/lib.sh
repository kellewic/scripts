## Only run this if we haven't been sourced before
if [ -z "$_sbl_lib" ]; then
	declare -a _sbl_on_exit_commands
fi

_sbl_lib=1

## Loads a library if it's not already loaded. Can be called with one or
## many libraries to load.
function load_library()
{
    local _my_path=$(dirname $0)/sbl
	local lib
	local lib_file
	local loaded_lib

	for file in "$@"; do
        lib=$(basename $file)
		lib_file="$_my_path/$lib"

		if [ -e "$lib_file.sh" ]; then
			loaded_lib="_sbl_$lib"
			[ -z "${!loaded_lib}" ] && . "$lib_file.sh"
		fi
	done
}

## Exit functions taken from the following URL with only minor edits: 
## http://www.linuxjournal.com/content/use-bash-trap-statement-cleanup-temporary-files
##
## Run on-exit commands
function on_exit()
{
	for i in "${_sbl_on_exit_commands[@]}"; do
		eval $i
	done
}

## Add commands to execute on EXIT
function on_exit_add()
{
	## Add command to exit array
	local n=${#_sbl_on_exit_commands[*]}
	_sbl_on_exit_commands[$n]="$*"

	## Set exit function on first call
	[ $n -eq 0 ] && trap on_exit EXIT
}

