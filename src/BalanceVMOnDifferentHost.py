#!/usr/bin/python2
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
import re
from subprocess import call

DEBUG = 0

VERSION = "0.2"

SHOSTNAME = ''
SPORT = ''
SPROTOCOL = ''
ENGINE_CONN = ''
SUSERNAME = ''
SPASSWORD = ''

EXIT_ON = ''

parser = OptionParser()
usagestr = "usage: %prog [--debug NUMBER] --authfile AUTHFILE --datacenter DATACENTERNAME --vmignore filename-of-vms-to-ignore"

parser = OptionParser(usage=usagestr, version="%prog Version: " + VERSION)

parser.add_option("--authfile", type="string",dest="AUTH_FILE", 
                  help="Authorization File name")

parser.add_option("--datacenter", type="string",dest="DATACENTER", 
                  help="Data Center name where try to balance VMs")

parser.add_option("--vmignore", type="string",dest="VMIGNORE", 
                  help="File name of VMs to ignore")

parser.add_option("-d", "--debug", type="int",dest="DEBUGOPT",
                  help="Print debug information")

(options, args) = parser.parse_args()

if options.AUTH_FILE == "" or not options.AUTH_FILE:
    parser.error("incorrect number of arguments")
    sys.exit(1)

if options.DATACENTER == "" or not options.DATACENTER:
    parser.error("incorrect number of arguments")
    sys.exit(1)

if options.VMIGNORE == "" or not options.VMIGNORE:
    parser.error("incorrect number of arguments")
    sys.exit(1)

AUTH_FILE = options.AUTH_FILE
DATACENTER = options.DATACENTER
VMIGNORE = options.VMIGNORE

if options.DEBUGOPT:
    if type( options.DEBUGOPT ) == int:
        DEBUG = int( options.DEBUGOPT )
else:
    DEBUG = 0

if( DEBUG > 0 ):
    print "Authorization filename: '" + AUTH_FILE + "'"
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
    if( DEBUG > 0 ):
        print "Try to read Username from " + AUTH_FILE
    SUSERNAME = Config.get("Auth", "Username")
    if( DEBUG > 0 ):
        print "Found Username: " + SUSERNAME
        print "Try to read Password from " + AUTH_FILE
    SPASSWORD = Config.get("Auth", "Password")
    if( DEBUG > 0 ):
        print "Found Password: ***********"
        print "Try to read Hostname from " + AUTH_FILE
    SHOSTNAME = Config.get("Auth", "Hostname")
    if( DEBUG > 0 ):
        print "Found Hostname: " + SHOSTNAME
        print "Try to read protocol from " + AUTH_FILE
    SPROTOCOL = Config.get("Auth", "Protocol")
    if( DEBUG > 0 ):
        print "Found Protocol: " + SPROTOCOL
        print "Try to read Port from " + AUTH_FILE
    SPORT = Config.get("Auth", "Port")
    if( DEBUG > 0 ):
        print "Found Port: " + SPORT
    ENGINE_CONN = SPROTOCOL + '://' + SHOSTNAME + ':' + SPORT
    if( DEBUG > 0 ):
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
        if( DEBUG > 0 ):
            print "DC " + datacentername + " is present...continue"
    dcstat = dc.get_status().state
    if dcstat != "up":
        print "Error: DC " + datacentername + " is not up... Exit"
        sys.exit(1)

def checkVMNameAndOdd( vmname ):
    try:
        searchObj = re.search( r'^(\D\w*\D)(\d*)$', vmname, re.M|re.I)
        if len( searchObj.groups() ) == 2:
            if( DEBUG > 0):
                print ( "For VM %s found pattern %s and digit %s" %(vmname, searchObj.group(1), searchObj.group(2)))
            # now check if is odd
            if ( int( searchObj.group(2) ) % 2 == 0 ):
                return False
            else:
                return True
    except:
        if( DEBUG > 0 ):
            print "Error when trying to find pattern"
        return False

def vmNamePlusOne( vmname ):
    try:
        searchObj = re.search( r'^(\D\w*\D)(\d*)$', vmname, re.M|re.I)
        if len( searchObj.groups() ) == 2:
            i = int( searchObj.group(2) )
            i = i + 1
            vm2 = str( searchObj.group(1) )
            vm2 =  vm2 + str(i).zfill( len( searchObj.group(2) ) )
            if( DEBUG > 0):
                print ( "For VM %s build second VM name (plus one) %s" %( vmname, vm2 ) )
            return vm2
    except:
        print "Error: Error on vmNamePlusOne...Exit"
        sys.exit(1)

def launchMigration( vm1, vm2 ):
    try:
        d = os.path.dirname(os.path.realpath(__file__))
        if( DEBUG > 1):
            print ( "Directory containing executables: %s" %( d ) )
        fexec = d + "/MigrateVM.py"
        if( DEBUG > 1):
            print ( "Full path of executable: %s" %(fexec) )
        if DEBUG > 0:
            call([ fexec, "--debug", str(DEBUG), "--authfile", AUTH_FILE, "--vmname1", vm1, "--vmname2", vm2 ])
        else:
            call([ fexec, "--authfile", AUTH_FILE, "--vmname1", vm1, "--vmname2", vm2 ])
    except Exception,e:
        if( DEBUG > 0):
            print "Error launching MigrateVM.py...Skip"
            print str(e)
        return

# connect to engine
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
                            if( DEBUG > 0):
                                print "VM " + vm.get_name() + " is on file " + VMIGNORE + "...skipping"
                if SKIPVM:
                    continue
                else:
                    if( DEBUG > 0):
                        print "Check VM name " + vm.get_name() 
                    if checkVMNameAndOdd( vm.get_name() ):
                        if( DEBUG > 0):
                            print ("VM %s is odd, so is a candidate for balance" %(vm.get_name()))
                        vm1 = vm.get_name()
                        vm2 = vmNamePlusOne( vm1 )
                        if (vm2 != None) and vm2 != "":
                            launchMigration(vm1, vm2)
            else:
                if( DEBUG > 0 ):
                    print "VM " + vm.get_name() + " is not up...skipping"
    
except:
    if EXIT_ON == '':
        print 'Error: Connection failed to server: ' + ENGINE_CONN
    else:
        print 'Error on ' + EXIT_ON
finally:
    if api != None:
        api.disconnect()