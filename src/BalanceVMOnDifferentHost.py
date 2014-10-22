#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
        Autore: Amedeo Salvati
        email: amedeo@linux.com
        
        
        Copyright (C) 2014 Amedeo Salvati.  All rights reserved.
        
        This program is free software; you can redistribute it and/or
        modify it under the terms of the GNU General Public License
        as published by the Free Software Foundation; either version 2
        of the License, or (at your option) any later version.
        
        This program is distributed in the hope that it will be useful,
        but WITHOUT ANY WARRANTY; without even the implied warranty of
        MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
        GNU General Public License for more details.
        
        You should have received a copy of the GNU General Public License
        along with this program; if not, write to the Free Software
        Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
        
        Amedeo Salvati
        22-10-2014
        Try to balance VM with same hostname to different hypervisor
"""

from ovirtsdk.xml import params
from ovirtsdk.api import API
from time import sleep
import os, sys
from optparse import OptionParser
from string import count
import ConfigParser
import os.path

# Set > 0 if you whant print terminal information
DEBUG = 1

VERSION = "0.1"

SHOSTNAME = ''
SPORT = ''
SPROTOCOL = ''
ENGINE_CONN = ''
SUSERNAME = ''
SPASSWORD = ''

#FIXME: make this variable parameter
AUTH_FILE = '/home/amedeo/DR/.authpass'

EXIT_ON = ''

parser = OptionParser()
usagestr = "usage: %prog [options] --datacenter DATACENTERNAME --vmignore filename-of-vms-to-ignore"

parser = OptionParser(usage=usagestr, version="%prog Version: " + VERSION)

parser.add_option("--datacenter", type="string",dest="DATACENTER", 
                  help="Data Center name where try to balance VMs")

parser.add_option("--vmignore", type="string",dest="VMIGNORE", 
                  help="File name of VMs to ignore")

(options, args) = parser.parse_args()

if options.DATACENTER == "" or not options.DATACENTER:
    parser.error("incorrect number of arguments")
    sys.exit(1)

if options.VMIGNORE == "" or not options.VMIGNORE:
    parser.error("incorrect number of arguments")
    sys.exit(1)

DATACENTER = options.DATACENTER
VMIGNORE = options.VMIGNORE

if( DEBUG > 0 ):
    print "Data Center name: '" + DATACENTER + "'"
    print "VMIGNORE file: '" + VMIGNORE + "'"

# check if file VMIGNORE exist
try:
    if os.path.isfile(VMIGNORE):
        if( DEBUG > 0 ):
            print 'Using file ' + VMIGNORE + ' to ignore VM'
    else:
        sys.exit(1)
except:
    print 'Error: file ' + VMIGNORE + ' does not exist exit'
    sys.exit(1)

# get auth user / pass
try:
    Config = ConfigParser.ConfigParser()
    Config.read(AUTH_FILE)
    if len( Config.sections() ) == 0:
        print "Error: Wrong auth file: " + AUTH_FILE + ", now try to use default /root/DR/.authpass"
        AUTH_FILE = '/root/DR/.authpass'
        Config.read(AUTH_FILE)
        if len( Config.sections() ) == 0:
            print "Error: Wrong auth file: " + AUTH_FILE + ", now exit"
            sys.exit(1)
    print "Try to read Username from " + AUTH_FILE
    SUSERNAME = Config.get("Auth", "Username")
    print "Found Username: " + SUSERNAME
    print "Try to read Password from " + AUTH_FILE
    SPASSWORD = Config.get("Auth", "Password")
    print "Found Password: ***********"
    print "Try to read Hostname from " + AUTH_FILE
    SHOSTNAME = Config.get("Auth", "Hostname")
    print "Found Hostname: " + SHOSTNAME
    print "Try to read protocol from " + AUTH_FILE
    SPROTOCOL = Config.get("Auth", "Protocol")
    print "Found Protocol: " + SPROTOCOL
    print "Try to read Port from " + AUTH_FILE
    SPORT = Config.get("Auth", "Port")
    print "Found Port: " + SPORT
    ENGINE_CONN = SPROTOCOL + '://' + SHOSTNAME + ':' + SPORT
    print "Connection string: " + ENGINE_CONN
except:
    print "Error on reading auth file: " + AUTH_FILE
    sys.exit(1)

def checkDCExist( datacentername ):
    if( DEBUG > 0 ):
        print "Check if DC exist and is up: '" + datacentername + "'"
    dc = api.datacenters.get(name=datacentername)
    if dc == None:
        print "Error: DC " + datacentername + " doesn't exist... Exit"
        sys.exit(1)
    else:
        print "DC " + datacentername + " is present...continue"
    dcstat = dc.get_status().state
    if dcstat != "up":
        print "Error: DC " + datacentername + " is not up... Exit"
        sys.exit(1)

# connect to rhevm
try:
    if( DEBUG > 0):
        print 'Now try to connect to the engine: ' + ENGINE_CONN
    
    api = None
    api = API(ENGINE_CONN, insecure=True, username=SUSERNAME, password=SPASSWORD)
    if( DEBUG > 0):
        print 'Connection established to the engine: ' + ENGINE_CONN
    
    # verify if datacenter is up
    EXIT_ON = "CHECKDC"
    checkDCExist(DATACENTER)
    
    # list cluster
    EXIT_ON = 'LISTCLUSTER'
    clulist = api.clusters.list( "datacenter=" + DATACENTER )
    for clu in clulist:
        if( DEBUG > 0):
            print "Found cluster " + clu.get_name()
        
        # now list all VMs on cluster
        EXIT_ON = 'LISTVM'
        vmlist = api.vms.list( "cluster=" + clu.get_name(), max=10000)
        for vm in vmlist:
            if( DEBUG > 0):
                print "Check VMNAME for VM " + vm.get_name()
            
            # check if vm is up
            if vm.get_status().state == "up":
                if( DEBUG > 0):
                    print "VM " + vm.get_name() + " is up"
                
                # now check if VM is inside vmignore file
                SKIPVM = False
                with open( VMIGNORE ) as f:
                    for line in f:
                        if vm.get_name() == line.strip():
                            SKIPVM = True
                if SKIPVM:
                    print "VM " + vm.get_name() + " is on file " + VMIGNORE + "...skipping"
                    continue
                else:
                    print "MIGRATING " + vm.get_name() 
            else:
                print "VM " + vm.get_name() + " is not up...skipping"
    
except:
    if EXIT_ON == '':
        print 'Error: Connection failed to server: ' + ENGINE_CONN
    else:
        print 'Error on ' + EXIT_ON
finally:
    if api != None:
        api.disconnect()