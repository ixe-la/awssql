#!/usr/bin/env python

import psycopg2
import ostore
import sys
import json
import pprint

#acctnick='KJDEV-us-west-1'
assert len(sys.argv) == 2

acctnick=sys.argv[1]
workpath="~/AWS_Rancid"

#
# database specifications
#
# create table sgins ( awsacct text, region text, vpcid text, sgid text, instanceid text );
#
#conn_string = "host='localhost' dbname='kamebamon' user='ec2-user'"
conn_string = "dbname='kamebamon' user='ec2-user'"

# read current directory name
# determine profile, eg KJPROD-sa-east-1
# select from account info and load variables



conn = psycopg2.connect(conn_string)
cur = conn.cursor()

d=ostore.load(workpath, acctnick)

#
# create table locator (acctnick text, awsacct text, region text)
#
try:
    locatorquery="SELECT awsacct, region FROM locator WHERE acctnick = %s"
    cur.execute(locatorquery, (acctnick,) )
    result=cur.fetchone()
    (awsacct, region) = result
    
except psycopg2.DatabaseError, e:
    if conn:
        conn.rollback()
        print 'Error %s' % e
    sys.exit(1)


#
# sgins: map of application of security groups to instances.
# if a security group is not listed here then there are no instances in it.
#
try:
    print "I declare awsacct "+awsacct+" in region "+region+"."
    cleanquery='DELETE FROM sgins where awsacct=%s and region=%s'
    cur.execute(cleanquery, (awsacct, region) ) 
    for ridx, r in enumerate(d['Reservations']):
           for iidx, i in enumerate(r['Instances']):
                     for sgidx, sg in enumerate(i['SecurityGroups']):
                                  query="INSERT INTO sgins (awsacct, region, vpcid, sgid, instanceid) VALUES (%s, %s, %s, %s, %s)"
                                  cur.execute(query, ( awsacct, region, i.get('VpcId'), sg['GroupId'], i['InstanceId'] ))
#
# create table sgnetsrc (awsacct text, region text, vpcid text, sgid text, groupname text, description text, proto text, cidrip cidr, fromport integer, toport integer, relaxedcidr text);
#
    cleanquery='DELETE FROM sgnetsrc where awsacct=%s and region=%s'
    cur.execute(cleanquery, (awsacct, region) ) 
    for sgidx, sg in enumerate(d['SecurityGroups']):
# XXX no VPC in SG spec?
        for ippermsidx, ipperms in enumerate(sg['IpPermissions']):
            for iprangeidx, iprange in enumerate(ipperms['IpRanges']):
# fix case when bits are set to right of mask!
                    (netnumber, mask) = iprange['CidrIp'].split('/')
#                    print sg.get('VpcId'), sg['GroupId'], sg['GroupName'], sg['Description'], ipperms['IpProtocol'], ipperms.get('FromPort'), ipperms.get('ToPort'), iprange['CidrIp']
                    query="INSERT INTO sgnetsrc (awsacct, region, vpcid, sgid, groupname, description, proto, cidrip, fromport, toport, relaxedcidr) VALUES (%s,%s,%s,%s,%s,%s,%s,  set_masklen(%s::cidr,%s)  ,%s,%s,%s)"
                    cur.execute(query, ( awsacct, region, sg.get('VpcId'), sg['GroupId'], sg['GroupName'], sg['Description'], ipperms['IpProtocol'], netnumber, mask, ipperms.get('FromPort'), ipperms.get('ToPort'), iprange['CidrIp']) );
#
# create table networkinterfaces ( vpcid text, description text, macaddress macaddr, networkinterfaceid text, subnetid text, privateip inet, publicip inet);
#
    cleanquery='DELETE FROM networkinterfaces where awsacct=%s and region=%s'
    cur.execute(cleanquery, (awsacct, region) ) 
    for niidx, ni in enumerate(d['NetworkInterfaces']):
        for privipidx, privip in enumerate(ni['PrivateIpAddresses']):
#            print niidx, privipidx, ni['VpcId'], ni['Description'], ni['MacAddress'], ni['NetworkInterfaceId'], ni['SubnetId'], privip['PrivateIpAddress'], privip.get('PublicIp')
            query="INSERT INTO networkinterfaces (awsacct, region, vpcid, description, macaddress, networkinterfaceid, subnetid, privateip, publicip) VALUES (%s,%s,%s, %s,%s,%s,%s,%s,%s)"
            if privip.get('Association') != None:
               publicip=privip['Association']['PublicIp']
            else:
               publicip=None
            cur.execute(query, (awsacct, region, ni['VpcId'], ni['Description'], ni['MacAddress'], ni['NetworkInterfaceId'], ni['SubnetId'], privip['PrivateIpAddress'], publicip ) )

    conn.commit()


#
# create table instances (vpcid text, instanceid text, instancetype text, imageid text, name text, keyname text, launchtime text, state text)
#
    cleanquery='DELETE FROM instances where awsacct=%s and region=%s'
    cur.execute(cleanquery, (awsacct, region) ) 
    for ridx, r in enumerate(d['Reservations']):
           for iidx, i in enumerate(r['Instances']):
               if i.get('Tags')==None:
                   name=None
               else:
                   for tidx, t in enumerate(i['Tags']):
                      name=None
                      if t['Key']=='Name':
                         name=t['Value']
               
               query="INSERT INTO instances (awsacct, region, vpcid, instanceid, instancetype, imageid, name, keyname, launchtime, state) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
#               cur.execute(query, ( i.get('VpcId'), i['InstanceId'], i['ImageId'], name, i.get('KeyName'), i['LaunchTime'], i['State']  ))
#               print ( i.get('VpcId'), i['InstanceId'], i['InstanceType'], i['ImageId'], name, i.get('KeyName'), i['LaunchTime'], i['State']['Name'] )
               cur.execute(query, ( awsacct, region, i.get('VpcId'), i['InstanceId'], i['InstanceType'], i['ImageId'], name, i.get('KeyName'), i['LaunchTime'], i['State']['Name'] ))

# create table instanceinterfaces (vpcid text, instanceid text, networkinterfaceid text, isattached boolean, deviceindex integer);
    cleanquery='DELETE FROM instanceinterfaces where awsacct=%s and region=%s'
    cur.execute(cleanquery, (awsacct, region) ) 
    for ridx, r in enumerate(d['Reservations']):
           for iidx, i in enumerate(r['Instances']):
                 for niidx, ni in enumerate(i['NetworkInterfaces']):
#                     print i['InstanceId'], ni['NetworkInterfaceId'], ni['Attachment']['Status'], ni['Attachment']['DeviceIndex']
                     if ni['Attachment']['Status']=='attached':
                         attached='True'
                     else:
                         attached='False'
                     query="INSERT INTO instanceinterfaces (awsacct, region, vpcid, instanceid, networkinterfaceid, isattached, deviceindex) VALUES (%s,%s,%s, %s,%s,%s,%s)"
                     cur.execute(query, ( awsacct, region, i['VpcId'], i['InstanceId'], ni['NetworkInterfaceId'], attached, ni['Attachment']['DeviceIndex'] ) )


#
# create table lb (vpcid text, loadbalancername text, dnsname text, createdtime text, canonicalhostedzonename text, scheme text, sourcesecuritygroupname text);
# create table lbsubnet (vpcid text, loadbalancername text, subnetid text);
# create table lbsg (vpcid text, loadbalancername text, securitygroupid text);
    cleanquery='DELETE FROM lb where awsacct=%s and region=%s'
    cur.execute(cleanquery, (awsacct, region) ) 
    cleanquery='DELETE FROM lbsubnet where awsacct=%s and region=%s'
    cur.execute(cleanquery, (awsacct, region) ) 
    cleanquery='DELETE FROM lbsg where awsacct=%s and region=%s'
    cur.execute(cleanquery, (awsacct, region) ) 
    cleanquery='DELETE FROM lbins where awsacct=%s and region=%s'
    cur.execute(cleanquery, (awsacct, region) ) 
    for lbidx, lb in enumerate(d['LoadBalancers']):
#        print lb.get('VPCId'), lb['LoadBalancerName'], lb['DNSName'], lb['CreatedTime'], lb.get('CanonicalHostedZoneName'), lb['Scheme'], lb['SourceSecurityGroup']['GroupName']
        query="INSERT INTO lb (awsacct, region, vpcid, loadbalancername, dnsname,createdtime, canonicalhostedzonename, scheme, sourcesecuritygroupname) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)"
        cur.execute(query, ( awsacct, region, lb.get('VPCId'), lb['LoadBalancerName'], lb['DNSName'], lb['CreatedTime'], lb.get('CanonicalHostedZoneName'), lb['Scheme'], lb['SourceSecurityGroup']['GroupName'] ) )
        for subnetidx, subnet in enumerate(lb['Subnets']):
#            print lb.get('VPCId'), lb['LoadBalancerName'], subnet
            query="INSERT INTO lbsubnet (awsacct, region, vpcid, loadbalancername, subnetid) VALUES (%s, %s,%s,%s,%s)"
            cur.execute(query, (awsacct, region, lb.get('VPCId'), lb['LoadBalancerName'], subnet ) )
        for sgidx, sg in enumerate(lb['SecurityGroups']):
#            print lb.get('VPCId'), lb['LoadBalancerName'], sg
            query="INSERT INTO lbsg (awsacct, region, vpcid, loadbalancername, securitygroupid) VALUES (%s, %s, %s, %s, %s)"
            cur.execute(query, (awsacct, region, lb.get('VPCId'), lb['LoadBalancerName'], sg) )
#
# create table lbins ( awsacct text, region text, vpcid text, loadbalancername text, instanceid text )
#
        for insidx, instance in enumerate(lb['Instances']):
            query="INSERT INTO lbins (awsacct, region, vpcid, loadbalancername, instanceid) VALUES (%s,%s,%s,%s,%s)"
#            print "Query " + (query % ( awsacct, region, lb.get('VPCId'), lb['LoadBalancerName'], instance['InstanceId'] ) )
            cur.execute(query, ( awsacct, region, lb.get('VPCId'), lb['LoadBalancerName'], instance['InstanceId'] ) )

#
# create table lblistener ( awsacct text, region text, vpcid text, loadalancername text, loadbalancerport, protocol, instanceport, instanceprotocol, sslcertificateid )
#


#
# create table sg (vpcid text, sgid text, securitygroupname text, descr text);
#
    cleanquery='DELETE FROM sg where awsacct=%s and region=%s'
    cur.execute(cleanquery, (awsacct, region) ) 
    for sgidx, sg in enumerate(d['SecurityGroups']):
        query="INSERT INTO sg (awsacct, region, vpcid, securitygroupname, sgid, descr) VALUES (%s, %s, %s,%s,%s,%s)"
        cur.execute(query, (awsacct, region, sg.get('VpcId'), sg['GroupName'], sg['GroupId'], sg['Description']) )
    conn.commit()

except psycopg2.DatabaseError, e:
    if conn:
           conn.rollback() 
    print 'Error %s' % e    
    sys.exit(1)



    