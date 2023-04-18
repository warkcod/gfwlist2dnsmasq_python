#!/usr/bin/env python  
#coding=utf-8
#  
# Generate a list of dnsmasq rules with ipset for gfwlist
# Ref https://github.com/gfwlist/gfwlist   
 
import urllib.request, urllib.error, urllib.parse 
import re
import os
import datetime
import base64
import shutil
import ssl
import argparse
 
mydnsip = '127.0.0.1'
mydnsport = '5353'
ipsetname = 'gfwlist'
customGFWListFile = 'customGfwList.txt'
finalRulesFile = './dnsmasq_list.conf'

# the url of gfwlist
baseurl = 'https://raw.githubusercontent.com/gfwlist/gfwlist/master/gfwlist.txt'
# match comments/title/whitelist/ip address

tmpfile = '/tmp/gfwlisttmp'
# do not write to router internal flash directly
outfile = '/tmp/dnsmasq_list.conf'

def update_domains_from_file(tmpfile, outputfs, mydnsip, mydnsport, ipsetname, domainlist):
    comment_pattern = '^\!|\[|^@@|^\d+\.\d+\.\d+\.\d+'
    domain_pattern = '(?:[\w\-]*\*[\w\-]*\.)?([\w\-]+\.[\w\.\-]+)[\/\*]*'
    ip_pattern = re.compile(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b')

    tfs = open(tmpfile, 'r')

    for line in tfs.readlines():	
        if re.findall(comment_pattern, line):
            print('this is a comment line: ' + line)
            #fs.write('#' + line)
        else:
            domain = re.findall(domain_pattern, line)
            if domain:
                try:
                    found = domainlist.index(domain[0])
                    print(domain[0] + ' exists.')
                except ValueError:
                    if ip_pattern.match(domain[0]):
                        print('skipping ip: ' + domain[0])
                        continue
                    print('saving ' + domain[0])
                    domainlist.append(domain[0])
                    outputfs.write('server=/%s/%s#%s\n'%(domain[0],mydnsip,mydnsport))
                    outputfs.write('ipset=/%s/%s\n'%(domain[0],ipsetname))
            else:
                print('no valid domain in this line: ' + line)

    tfs.close()

parser = argparse.ArgumentParser(description='Generate gfwList file for DNSMasq from gfwlist.txt')
parser.add_argument('--input_file', help='The local gfwlist.txt input file.')
parser.add_argument('--verbose', action='store_true', help='Print verbose output.')
parser.add_argument('--version', action='version', version='%(prog)s 2.0')
try:
    args = parser.parse_args()
    print('Input file:', args.input_file)
    if args.verbose:
        print('Verbose output is on.')
    else:
        print('Verbose output is off.')
except argparse.ArgumentError:
    parser.print_usage()
    exit()
    
if args.input_file:
    print("Reading from local input file...")
    content = open(args.input_file, 'r').read()
else:
    print('fetching list...')
    if hasattr(ssl, '_create_unverified_context'):
         ssl._create_default_https_context = ssl._create_unverified_context
    content = urllib.request.urlopen(baseurl, timeout=15).read() 
    
decode_content = base64.b64decode(content).decode('utf-8')
 
# write the decoded content to file then read line by line
tfs = open(tmpfile, 'w')
tfs.write(decode_content)
tfs.close()

print('page content fetched, analysis...')


fs =  open(outfile, 'w')
fs.write('# gfw list ipset rules for dnsmasq\n')
fs.write('# updated on ' + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + '\n')
fs.write('#\n')

# remember all blocked domains, in case of duplicate records
domainlist = []

update_domains_from_file(tmpfile, fs, mydnsip, mydnsport, ipsetname, domainlist)

#add custom gfw list
if os.path.exists(customGFWListFile) and os.path.getsize(customGFWListFile) > 0:
     fs.write('# CUSTOM_GFW_LIST:\n')
     update_domains_from_file(customGFWListFile, fs, mydnsip, mydnsport, ipsetname, domainlist)
else:
    print('File does not exist or is empty. %s', customGFWListFile)

print('write extra domain done')

fs.close();
print('moving generated file to dnsmasq directory')
shutil.move(outfile, finalRulesFile)
 
print('done!')
