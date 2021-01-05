_sbl_net=1

function inet_aton()
{
	IP=$1
	IPNUM=0

	for (( i=0 ; i<4 ; ++i )); do
		((IPNUM+=${IP%%.*}*$((256**$((3-${i}))))))
		IP=${IP#*.}
	done

	echo $IPNUM 
}

function inet_ntoa()
{
	echo -n $(($(($(($((${1}/256))/256))/256))%256)). 
	echo -n $(($(($((${1}/256))/256))%256)). 
	echo -n $(($((${1}/256))%256)). 
	echo $((${1}%256)) 
}
