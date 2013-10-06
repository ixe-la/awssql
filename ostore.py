#!/usr/bin/env python

import json
import os
import glob
#import jmespath
global data

#acctnick='KJPROD'

def load( workpath, acctnick ):

    workpath=os.path.expanduser(workpath)
# even if "latest" is moved during processing, the directory we are in will not change.
    os.chdir(workpath+"/"+acctnick+"/latest")
    data={}

# specify the path to load

    for q in ["availability_zones", "instances", "internet_gateways", "network_acls", "network_interfaces", "route_tables", "security_groups", "subnets", "vpcs", "vpn_connections", "vpn_gateways"]:
        filename=glob.glob("*_"+q)[0]
        print filename
        json_data=open(filename)

# merge the data
        data = dict( data.items() + json.load(json_data).items() )

# delete the ResponseMetadata crap
    trash=data.pop("ResponseMetadata", None)

# this one is different because there is no responsemetadata crap
    for q in ["load_balancers"]:
        filename=glob.glob("*_"+q)[0]
        print filename
        json_data = '{ "LoadBalancers": ' + open(filename).read() + '}'
        data = dict( data.items() + json.loads(json_data).items() )

    return data

# example notes:
# load me in interactive with import ostore
# 
#
# sorted(ostore.data.keys())
#
# sorted is a builtin method, not a method of list. so you put it first.

# len(ostore.data['SecurityGroups'][2]["IpPermissions"])
# gives the number of elements inside the 3rd security group's IpPermissions (which is ingress, btw).
#
# type(whatever)

#
# Pretty Print, to valid JSON mind you:
# import json
# json.dumps(ostore.data['SecurityGroups'][2]["IpPermissions"][0], sort_keys=True)

