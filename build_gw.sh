#!/bin/bash
set -e

cat b.tsv | while read REGION AMI SUBNET0ID SUBNET1ID ETH0IP ETH1IP GROUPSET NAME ; do
echo REGION=$REGION
echo AMI=$AMI
echo SUBNET0ID=$SUBNET0ID
echo SUBNET1ID=$SUBNET1ID
echo ETH0IP=$ETH0IP
echo ETH1IP=$ETH1IP
echo GROUPSET=$GROUPSET
echo NAME=$NAME

GOTIME=`date --iso=s`
SIZE=m2.4xlarge
#SIZE=m1.xlarge
KEY=security-keys

echo $REGION "${NAME}" $AMI $ETH0IP $ETH1IP
echo $GOTIME: creating network interface in $REGION in $SUBNET1ID with IP $ETH1IP
echo "aws ec2 create-network-interface --profile KJPROD --region $REGION --subnet-id $SUBNET1ID --private-ip-address $ETH1IP"
aws ec2 create-network-interface --profile KJPROD --region $REGION --subnet-id $SUBNET1ID --private-ip-address $ETH1IP > ~/cni-result-$GOTIME 

NEWIFID=`cat ~/cni-result-$GOTIME | grep NetworkInterfaceId | sed 's/.*: "//;s/".*//'`
echo NEWIFID=$NEWIFID
if [[ -z "$NEWIFID" ]] ; then 
    exit 1
fi

echo $GOTIME: starting instance in $REGION of $AMI size $SIZE with $ETH0IP in $SUBNET0ID
aws ec2 run-instances --profile KJPROD \
     --region $REGION \
     --image-id $AMI \
     --min-count 1 \
     --max-count 1 \
     --instance-type $SIZE \
     --key-name $KEY \
     --subnet-id $SUBNET0ID \
     --private-ip-address $ETH0IP \
> ~/run-result-$GOTIME
INSTANCEID=`cat ~/run-result-$GOTIME | grep InstanceId | sed 's/.*: "//;s/".*//'`
OLDIFID=`cat ~/run-result-$GOTIME | grep NetworkInterfaceId | sed 's/.*: "//;s/".*//'`
echo INSTANCEID=$INSTANCEID
if [[ -z "$INSTANCEID" ]] ; then 
    exit 1
fi
echo OLDIFID=$OLDIFID
if [[ -z "$OLDIFID" ]] ; then 
    exit 1
fi

echo $GOTIME: assigning tag "${NAME}" for $INSTANCEID
aws ec2 --profile KJPROD --region $REGION create-tags \
     --resource $INSTANCEID --tags '{ "key":"Name","value":"'"${NAME}"'" }' > ~/tag-result-$GOTIME

#note, you can't stop an instance before it finishes running. so don't get too excited.

#echo Sleeping for 60 seconds while instance starts
#sleep 60


status=ng
while [ "$status" '!=' running ] ; do 
    output=`aws ec2 --profile KJPRODSEC --region $REGION describe-instance-status --instance-id $INSTANCEID`
    status=`echo "${output}" | grep Name | head -n1 | sed 's/.*": "//;s/".*//'`
    echo current status of $INSTANCEID is $status
done

echo $GOTIME: attaching interface $NEWIFID to $INSTANCEID
aws ec2 attach-network-interface --profile KJPROD --region $REGION --network-interface-id $NEWIFID --instance-id $INSTANCEID --device-index 1 > ~/ani-result-$GOTIME

echo $GOTIME: will modify $NEWIFID $OLDIFID with groupset $GROUPSET: `cat $GROUPSET`
GROUPEN=`cat $GROUPSET`
echo GROUPEN: $GROUPEN

for interface in $NEWIFID $OLDIFID ; do 
    echo "aws ec2 modify-network-interface-attribute --profile KJPROD --region $REGION --network-interface-id $interface --groups $GROUPEN"
    aws ec2 modify-network-interface-attribute --profile KJPROD --region $REGION --network-interface-id $interface --groups $GROUPEN > ~/grp-result-$GROUPSET-$GOTIME
done

echo '=======' Summary: GT $GOTIME I $INSTANCEID ONIC $OLDIFID NNIC $NEWIFID ETH0 $ETH0IP ETH1 $ETH1IP name "${NAME}"
done



