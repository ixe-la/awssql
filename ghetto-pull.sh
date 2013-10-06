#!/bin/bash


# eventually we should
# sort output
# delete the request metadata portion (for affected query types)
#
# i believe both of these can be done with Pyfun
# 

export PATH=~/bin/:$PATH
export AWS_CONFIG_FILE=/home/ec2-user/.awsconfig

ts=`date +%Y%m%d.%H%M%S` ; for acct in KJPROD KJDEV ; do 
    for r in `~/bin/list_regions.sh` ; do
        p=${acct}-${r}
        d=~/AWS_Rancid/$p/$p_$ts 
        mkdir -p $d  
        (cd $d ; descr.sh $acct $r) 
        ln -nsf $d ~/AWS_Rancid/$p/latest
        ~/Pyfun/build_tables.py ${acct}-${r}
    done
done

