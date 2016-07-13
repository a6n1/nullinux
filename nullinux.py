#!/usr/bin/python2.7
# nullinux.py
# SMB null session enumeration tool for Linux
# MIT license 2016
# Author: m8r0wn

# Usage
#-----------------------------------------------
# nullinux is meant to be a quick enumeration of
# SMB shares on a network. This can be done
# with either an smb null session or given username
# and password. 

# Disclaimer
#------------------------------------------------
# This tool was designed to be used only with proper
# consent. The author is in no way responsible 
# for your use of this tool or its effects.


import sys
import logging
logging.getLogger("scapy.runtime").setLevel(logging.ERROR)
from scapy.all import *
import socket
import commands
import datetime


def banner():
    print"""

              nullinux | %s
    SMB Null Session Enumeration Tool

HOST:
  -U                  	Set username    (optional)
  -P                  	Set Password    (optional)

CONNECTION:
  -sT                 	TCP Connection scan
  -sS                 	Stealth Scan 	(Default)
  -sN                 	Don't Check for open smb-related ports(Just connect)
  -p			Specify ports 	(Default: 139,445) 		      	

SHARES:
  --enumshares        	Enumerate possible shares
  -S share1,share2..  	Specify share(s)
  -A                  	Try shares [IPC$, ADMIN$, C$]

USERS:
  --enumusers         	Enumerate users
  --range #-#         	Specify range for RID cycling (Default range: 0-35,500-535)

MORE OPTIONS:
  --all		      	Invoke all options [enumshares, enumusers]
  -v	       	      	verbose output
  -h	       	      	help

EXAMPLES:
  ./nullinux.py -sT -v --enumusers 10.0.0.1-10
  ./nullinux.py -sN -U Administrator -P password --all 10.0.0.10
  ./nullinux.py 10.0.0.1-255

    """ % (version)
    sys.exit(0)


def startUp():
    currentTime = datetime.datetime.now().strftime('%m-%d-%Y %H:%M')
    print"\nStarting nullinux %s | %s" % (version, currentTime)


def closing():
    print "\n[-] Process Stopped: Closing nullinux...\n"
    sys.exit(0)


#Port scan: Stealth Scan (Default)/TCP Scan based on response flag sent.
def portScan(rsp_flag):
    global targets_enum
    print "[+] Port scanning targets"
    #Look for open SMB port for each target in list
    for t in targets_portScan:
        openPorts = 0
        for p in ports:
	    try:
		srcPort = RandShort()
		scan = sr1(IP(dst=t)/TCP(sport=srcPort, dport=p, flags="S"), timeout=1, verbose=0)
		if (scan.haslayer(TCP)):
		    if (scan.getlayer(TCP).flags == 0x12):
			reset = sr(IP(dst=t)/TCP(sport=srcPort, dport=p, flags=rsp_flag),timeout=3, verbose=0)
			openPorts += 1
		        if verbose: print "    + %s : %s Open" % (t,p)
		    else:
		        if verbose: print "    - %s : %s Closed" % (t,p)
		else:
		    if verbose: print "    - %s : %s Closed" % (t,p)
	    except:
		if verbose: print "    - %s : %s Closed" % (t,p)
        if openPorts >= 1: targets_enum.append(t)
    #Exit if no SMB ports found
    if not targets_enum:
        if verbose:
            print "\n[-] No SMB ports detected\n"
            sys.exit(0)
        else:
            print "\n[-] No SMB ports detected, use -v for more information\n"
            sys.exit(0)
    else:
	print "\n"
        enumerate()


def enumerate():
    #start enumeration
    if enumusers: rid_cycling = enumerate_domain()
    for t in targets_enum:
	smb_info = "smbclient //%s/IPC$ -U %s%%%s -c exit" % (t, username, password)
        smb_info_output = commands.getstatusoutput(smb_info)
        for line in smb_info_output[1].splitlines():
            if "WARNING" in line:		pass
	    elif "BAD_NETWORK_NAME" in line: 	pass
            else:				print "[+] %s: %s" % (t, line)
	if enumshares and enumusers:
	    enumerate_shares(t)
	    enumerate_users(t, rid_cycling)
	elif enumshares: enumerate_shares(t)
	elif enumusers: enumerate_users(t, rid_cycling)
    if enumusers:
	print "\n[*] Found %s USER(S) and %s GROUP(S) for %s" % (len(users_collected), len(groups_collected), sys.argv[-1]) 	
	if not users_collected: 
	    print "[-] No Users Found\n[-] Closing\n"
	    sys.exit(0)
	else:
	    print "[*] Generating user list nullinux_users.txt"
	    #Create user list
	    openfile = open('nullinux_users.txt' , 'w')		    
	    for user in users_collected:
		if user == users_collected[-1]: openfile.write('%s' % user)
		else:				openfile.write('%s\n' % user)
	    openfile.close()
	    print "[+] File complete\n[*] Closing\n"
	    sys.exit(0)
    else:
        print "\n"
	sys.exit(0)


def enumerate_domain():
    global domain_sid
    global domain_name
    print "[*] Gathering Domain information"
    #Get domain information
    lsaquery = "rpcclient -c lsaquery -U %s%%%s %s" % (username, password, targets_enum[0])
    lsaquery_output = commands.getstatusoutput(lsaquery)
    for line in lsaquery_output[1].splitlines():
	if "Domain Name:" in line:
    	    label1, doamin_name = line.split(":")
    	    doamin_name = doamin_name.lstrip()
    	    doamin_name = doamin_name.rstrip()
    	    print "    +Domain Name: %s" % (doamin_name)
	elif "Domain Sid:" in line:
    	    label2, domain_sid = line.split(":")
    	    domain_sid = domain_sid.lstrip()
    	    domain_sid = domain_sid.rstrip()
    	    print "    +Domain SID: %s\n" % (domain_sid)
    #Retry domain information
    if not domain_sid and targets_enum[0] != targets_enum[-1]:
            print "    -Retrying Domain Informaiton..."
            lsaquery = "rpcclient -c lsaquery -U %s%%%s %s" % (username, password, targets_enum[-1])
            lsaquery_output = commands.getstatusoutput(lsaquery)
            for line in lsaquery_output[1].splitlines():
	        if "Domain Name:" in line:
           	    label1, doamin_name = line.split(":")
                    doamin_name = doamin_name.lstrip()
        	    doamin_name = doamin_name.rstrip()
        	    print "    +Domain Name: %s" % (doamin_name)
	        elif "Domain Sid:" in line:
        	    label2, domain_sid = line.split(":")
        	    domain_sid = domain_sid.lstrip()
        	    domain_sid = domain_sid.rstrip()
        	    print "    +Domain SID: %s\n" % (domain_sid)
    if not domain_sid:
        print "    -Error: Could not retrieve Domain Informaiton."
        print "    -RID Cycling has been disabled.\n"
	return False
    else:
	return True


def enumerate_shares(t):
    t_shares = []
    print "    [*] Enumerating shares for %s" % (t)
    enum_shares = "smbclient -L %s -U %s%%%s" % (t, username, password)
    enum_shares_output = commands.getstatusoutput(enum_shares)
    for line in enum_shares_output[1].splitlines():
	if "Domain=[" in line: 			pass
	elif line == "": 			pass
	elif "RESOURCE_NAME_NOT_FOUND" in line: pass
	elif "TCP disabled" in line: 		pass
	elif "WARNING" in line: 		pass
	elif "Sharename" in line: 		print 	"         ", line
	elif "---------" in line: 		print 	"         ", line
	elif "DENIED" in line: 			print 	"        -", line
	elif "disabled" in line: 		print 	"        -", line
	elif "failed" in line: 			print 	"        -", line
	else: 	
	    #Take shares found and add to t_shares list
	    share_string = line.split(' ')
	    s = share_string[0].lstrip()
	    s = s.rstrip()
	    if s not in shares: t_shares.append(s)				
	    print "        +", line
    #Enum directory from shares in global list
    for s in shares:
        enum_dir = "smbclient //%s/%s -U %s%%%s -c dir" % (t, s, username, password)
        enum_dir_output = commands.getstatusoutput(enum_dir)
        print "\n    [*] Enumerating Directory for %s @ %s" % (t,s)
        for line in enum_dir_output[1].splitlines():
	    if "Domain=[" in line: 			pass
	    elif line == "": 				pass
	    elif "RESOURCE_NAME_NOT_FOUND" in line: 	pass
	    elif "TCP disabled" in line: 		pass
	    elif "WARNING" in line: 			pass
	    elif "Sharename" in line: 			print 	"         ", line
	    elif "---------" in line: 			print 	"         ", line
	    elif "DENIED" in line: 			print 	"        -", line
	    elif "disabled" in line: 			print 	"        -", line
	    elif "failed" in line: 			print 	"        -", line
	    else: 					print 	"        +", line   
    #Enum directory from local target shares found				
    for s in t_shares:
        enum_dir = "smbclient //%s/%s -U %s%%%s -c dir" % (t, s, username, password)
        enum_dir_output = commands.getstatusoutput(enum_dir)
        print "\n    [*] Enumerating Directory for %s @ %s" % (t,s)
        for line in enum_dir_output[1].splitlines():
	    if "Domain=[" in line: 			pass
	    elif line == "": 				pass
	    elif "RESOURCE_NAME_NOT_FOUND" in line: 	pass
	    elif "TCP disabled" in line: 		pass
	    elif "WARNING" in line: 			pass
	    elif "Sharename" in line: 			print 	"         ", line
	    elif "---------" in line: 			print 	"         ", line
	    elif "DENIED" in line: 			print 	"        -", line
	    elif "disabled" in line: 			print 	"        -", line
	    elif "failed" in line: 			print 	"        -", line
	    else: 					print 	"        +", line


def enumerate_users(t, rid_cycling):
    global groups_collected
    global users_collected
    rids_collected 	= []
    known_usernames	= ['Administrator', 'Guest', 'krbtgt', 'root', 'bin']
    #Query user info with querydispinfo and enumdomusers
    print "\n    [*] Enumerating users for %s through querydispinfo:" % (t)
    enum_user = "rpcclient -c querydispinfo -U %s%%%s %s" % (username, password, t)
    enum_user_output = commands.getstatusoutput(enum_user)
    for line in enum_user_output[1].splitlines():
        if "DENIED" in line: 		pass #print 	"        -", line
        elif "error" in line: 		pass #print 	"        -", line
        elif "failed" in line: 		pass #print 	"        -", line
        elif "could not" in line: 	pass #print 	"        -", line
        elif "disabled" in line: 	pass #print 	"        -", line
        else:	
	    #Split output to get user			
	    name_split = line.split(": ")
            temp_name = name_split[4]
            temp_name = temp_name.split("Name")
            temp_name = temp_name[0].lstrip()
            temp_name = temp_name.rstrip()
            print "        +",temp_name
            if temp_name not in users_collected:
		users_collected.append(temp_name)
    print "\n    [*] Enumerating users for %s through enumdomusers:" % (t)
    enum_dom_user = "rpcclient -c enumdomusers -U %s%%%s %s" % (username, password, t)
    enum_dom_user_output = commands.getstatusoutput(enum_dom_user)	
    for line in enum_dom_user_output[1].splitlines():
        if "DENIED" in line: 		pass #print 	"        -", line
        elif "error" in line: 		pass #print 	"        -", line
        elif "failed" in line: 		pass #print 	"        -", line
        elif "could not" in line: 	pass #print 	"        -", line
        elif "disabled" in line: 	print 	"        -", line
        else:
	    #Split output to get user				
	    name_split = line.split("[")
	    temp_name = name_split[1]
            temp_name = temp_name.split("]")
            temp_name = temp_name[0].lstrip()
            temp_name = temp_name.rstrip()
            print "        +",temp_name
            if temp_name not in users_collected:
       	        users_collected.append(temp_name)
    #Enumerate known users through local security authority
    print "\n    [*] Enumerating users for %s through Local Security Authority" % (t)
    lsa_rids = "rpcclient -c lsaenumsid -U %s%%%s %s" % (username, password, t)
    lsa_rids_output = commands.getstatusoutput(lsa_rids)
    if verbose: print "        [*] RIDS:"
    for line in lsa_rids_output[1].splitlines():
	if "S-1-5-" in line:
	    rids_collected.append(line)
	    if verbose: print "            +",line
    if rids_collected:
	if verbose: print "        [*] Users:"
	for rid in rids_collected:
	    user_rid = "rpcclient -c 'lookupsids %s' -U %s%%%s %s" % (rid, username, password, t)
	    user_rid_output = commands.getstatusoutput(user_rid)
	    for line in user_rid_output[1].splitlines():
        	if "DENIED" in line: 		pass #print 	"        -", line
        	elif "INVALID_SID" in line: 	pass #print 	"        -", line
        	elif "error" in line: 		pass #print 	"        -", line
        	elif "failed" in line: 		pass #print 	"        -", line
        	elif "NONE_MAPPED" in line: 	pass #print 	"        -", line
		elif "*unknown*" in line: 	pass #print 	"        -", line
		elif "could not" in line: 	pass #print 	"        -", line
        	elif "disabled" in line: 	
		    if verbose:	print 	"            -", line
		    else:	print 	"        -", line
        	else:
	    	    #Split output to get user
		    temp_line = line.split(" (")
		    temp_num = temp_line[1].split(")")
		    if "1" in temp_num[0]: #temp_num[0] number of members
    			temp_name = temp_line[0].split("\\")
    			temp_name = temp_name[1].rstrip()
    			temp_name = temp_name.lstrip()
			if verbose: 	print "            +",temp_name
			else:		print "        +",temp_name
			if temp_name not in users_collected:
       	        	    users_collected.append(temp_name)
		    else:
			temp_name = temp_line[0].split("\\")
    			temp_name = temp_name[1].rstrip()
    			temp_name = temp_name.lstrip()
			print "        + %-35s (Network/Local Group)" % (temp_name)
    else: print "            -Could not enumerate LSA"
    #Enumerate users through known usernames
    print "\n    [*] Trying known usernames for %s" % (t)
    for user in known_usernames:
	known_user = "rpcclient -c \"lookupnames %s\" -U %s%%%s %s" % (user, username, password, t)
	known_user_output = commands.getstatusoutput(known_user)
	for line in known_user_output[1].splitlines():
            if "DENIED" in line: 		pass #print 	"        -" + line + " (%s)" % user
            elif "INVALID_SID" in line: 	pass #print 	"        -" + line + " (%s)" % user
            elif "error" in line: 		pass #print 	"        -" + line + " (%s)" % user
            elif "failed" in line: 		pass #print 	"        -" + line + " (%s)" % user
            elif "NONE_MAPPED" in line: 	pass #print 	"        -" + line + " (%s)" % user
	    elif "*unknown*" in line: 		pass #print 	"        -" + line + " (%s)" % user
	    elif "could not" in line: 		pass
	    elif "lsa pipe" in line:		pass
            elif "disabled" in line: 		print 	"        -", line
            else:
	    	#Split output to get user
	        temp_line = line.split(" S")
    	    	temp_name = temp_line[0].rstrip()
		temp_name = temp_name.lstrip()
		print "        +",temp_name
		if temp_name not in users_collected:
       	            users_collected.append(temp_name) 		
    #Enumerate users through rid cycling (if domain sid collected)
    if rid_cycling:
        print "\n    [*] Starting RID cycling for %s" % (t)
        for rid in rid_range:
            user_rid = "rpcclient -c \"lookupsids %s-%s\" -U %s%%%s %s" % (domain_sid, rid, username, password, t)
	    user_rid_output = commands.getstatusoutput(user_rid)
	    for line in user_rid_output[1].splitlines():
                if "DENIED" in line: 		pass #print 	"        -", line
                elif "INVALID_SID" in line: 	pass #print 	"        -", line
                elif "error" in line: 		pass #print 	"        -", line
                elif "failed" in line: 		pass #print 	"        -", line
                elif "NONE_MAPPED" in line: 	pass #print 	"        -", line
	        elif "*unknown*" in line: 	pass #print 	"        -", line
	        elif "could not" in line: 	pass #print 	"        -", line
                elif "disabled" in line: 	print 	"        -", line
                else:
		    #Split output to get user
		    temp_line = line.split(" (")
		    temp_num = temp_line[1].split(")")
		    if "1" in temp_num[0]: #temp_num[0] number of members
    			temp_name = temp_line[0].split("\\")
    			temp_name = temp_name[1].rstrip()
    			temp_name = temp_name.lstrip()
			print "        +",temp_name
			if temp_name not in users_collected:
       	        	    users_collected.append(temp_name)
		    else:
			temp_name = temp_line[0].split("\\")
    			temp_name = temp_name[1].rstrip()
    			temp_name = temp_name.lstrip()
			print "        + %-35s (Network/Local Group)" % (temp_name)
    #Enumerate users by group memberships
    print "\n    [*] Enumerating users by group memebership for %s" % (t)
    domain_groups = "rpcclient -c enumdomgroups -U %s%%%s %s" % (username, password, t)
    domain_groups_output = commands.getstatusoutput(domain_groups)
    for line in domain_groups_output[1].splitlines():
        if "DENIED" in line: 		pass #print 	"        -", line
        elif "error" in line: 		pass #print 	"        -", line
        elif "failed" in line: 		pass #print 	"        -", line
        elif "could not" in line: 	pass #print 	"        -", line
        elif "disabled" in line: 	print 	"        -", line
	else:
	    #Split output got get group
	    a = line.split("]")
	    b = a[0].split("[")
  	    domain_group = b[1].lstrip()
	    domain_group = domain_group.rstrip()
	    print "        [+] Group:",domain_group
	    if domain_group not in groups_collected:
 	 	groups_collected.append(domain_group)
	    #Enumerate memebers of the group
	    enum_members = "net rpc group members \'%s\' -U %s%%%s -I %s" % (domain_group, username, password, t)
            enum_members_output = commands.getstatusoutput(enum_members)
            for line in enum_members_output[1].splitlines():
	        if "DENIED" in line: 		print 	"            -", line
	        elif "disabled" in line: 	print 	"            -", line
	        elif "error" in line: 		print 	"            -", line
	        elif "failed" in line: 		print 	"            -", line
	        elif "could not" in line: 	print 	"            -", line
	        else:
		    #Split output to get user
    		    d = line.split("\\")
		    domain_user = d[1].lstrip()
		    domain_user = domain_user.rstrip()
		    print "            +",domain_user
    		    if domain_user not in users_collected:
		        users_collected.append(domain_user)


#Default Values
version		    =   "v3.0"
verbose	    	    =	False
enumshares  	    =	False
enumusers   	    =	False
scanType    	    =	"-sS"
username    	    =	"\"\""
password    	    =	"\"\""
domain_name	    =	""
domain_sid	    =	""
rid_range	    =   [] 
targets_portScan    =   []
targets_enum	    =	[]
shares      	    =	[]
ports		    =   [] 
users_collected	    =	[]
groups_collected    =	[]	

try:
    #Display banner
    if "-h" in sys.argv: banner()
    elif len(sys.argv)== 1: banner()

    #nullinux startup
    startUp()

    #Set Verbosity
    if "-V" in sys.argv: verbose = True
    if "-v" in sys.argv: verbose = True
    #Set Enumerate shares
    if "--enumshares" in sys.argv: enumshares = True
    #Set Enumerate Users
    if "--enumusers" in sys.argv: enumusers = True
    #Set all
    if "--all" in sys.argv: 
	enumshares 	= True
	enumusers	= True

        #Set custom range for brute_force
    if "--range" in sys.argv and "--enumusers" in sys.argv:
	temp_rid_range = sys.argv.index("--range")+1
	if "-" not in sys.argv[temp_rid_range]:
	    print "[-] Error: Incorrect range for brute_force"
	    sys.exit(0)
	rid_one, rid_two = sys.argv[temp_rid_range].split("-")
	for x in range(int(rid_one), int(rid_two)+1): rid_range.append(x)
    elif "--range" in sys.argv and "--all" in sys.argv:
	temp_rid_range = sys.argv.index("--range")+1
	if "-" not in sys.argv[temp_rid_range]:
	    print "[-] Error: Incorrect range for brute_force"
	    sys.exit(0)
	rid_one, rid_two = sys.argv[temp_rid_range].split("-")
	for x in range(int(rid_one), int(rid_two)+1): rid_range.append(x)
    elif "--enumusers" in sys.argv:
	for x in range(0, 35): rid_range.append(x)
	for x in range(500, 535): rid_range.append(x)	
    elif "--all" in sys.argv:
	for x in range(0, 35): rid_range.append(x)
	for x in range(500, 535): rid_range.append(x)

    #Set Targets
    target = sys.argv[-1]
    if "." not in target or len(target) < 7:
        print "[-] Error: No target detected.\n"
        sys.exit(0)
    elif "-" in target and "," in target:
        print "[-] Error: Invalid target detected.\n"
        sys.exit(0)
        #Range of IP's 127.0.0.1-255
    elif "-" in target:
        A, B = target.split("-")
        A1, A2, A3, A4 = A.split(".")
        for x in range(int(A4), int(B) + 1):
            target = A1 + "." + A2 + "." + A3 + "."
            target += `x`
            targets_portScan.append(target)
        #Multiple IP's 127.0.0.1,127.0.0.2,127.0.0.3
    elif "," in sys.argv[-1]:
        for t in sys.argv[-1].split(","):
            targets_portScan.append(t)
        #Single IP 127.0.0.1
    else:
        targets_portScan.append(target)

    #Set Shares
    if "-S" in sys.argv:
        ID = sys.argv.index("-S")+1
        for x in sys.argv[ID].split(","):
            shares.append(x)
    elif "-A" in sys.argv:
        shares = ['IPC$', 'ADMIN$', 'C$']
    else:
        shares = ['IPC$']

    #Set Username if provided
    if "-U" in sys.argv:
	username = sys.argv.index("-U")+1
	username = sys.argv[username]

    #Set Password if provided
    if "-P" in sys.argv:
	password = sys.argv.index("-P")+1
	password = sys.argv[password]	

    #Set Ports
    if "-p" in sys.argv:
        port_nums = sys.argv.index("-p")+1
	if type(port_nums) != int:
	    print "[-] Error: Invalid ports provided.\n"
        for x in sys.argv[port_nums].split(","):
            ports.append(x)
    else:
        ports = [139, 445]

    #Set Scan Type
    if "-sT" in sys.argv:
	scanType = "-sT"
    elif "-sN" in sys.argv:
        scanType = "-sN"
        #Input validation
    elif "-sS" and "-sT" in sys.argv:
        print "[-] Error: too many scan types listed.\n"
        sys.exit(0)
    elif "-sS" and "-sN" in sys.argv:
        print "[-] Error: too many scan types listed.\n"
        sys.exit(0)
    elif "-sT" and "-sN" in sys.argv:
        print "[-] Error: too many scan types listed.\n"
        sys.exit(0)

    #Check for open SMB ports
    if scanType == "-sS":
	rsp_flag = "R"
        portScan(rsp_flag)
    elif scanType == "-sT":
	rsp_flag = "AR"
	portScan(rsp_flag)
    elif scanType == "-sN":
	print "[*] SMB port scanner disabled"
        targets_enum = targets_portScan
        enumerate()
    else:
        print "[-] Error: Invalid scan used.\n"
        sys.exit(0)

except KeyboardInterrupt:
    closing()
