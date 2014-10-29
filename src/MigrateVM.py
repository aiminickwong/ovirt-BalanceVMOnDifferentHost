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
        23-10-2014
        Check if two VM is residing on the same hypervisor
"""

from ovirtsdk.xml import params
from ovirtsdk.api import API
from time import sleep
import os, sys
from optparse import OptionParser
from string import count
import ConfigParser

DEBUG = 0

VERSION = "0.1"

SHOSTNAME = ''
SPORT = ''
SPROTOCOL = ''
ENGINE_CONN = ''
SUSERNAME = ''
SPASSWORD = ''

EXIT_ON = ''


parser = OptionParser()
parser = OptionParser(usage="%prog [--debug NUMBER] --authfile AUTHFILE --vmname1 VM1 --vmname2 VM2", version="%prog Version: " + VERSION)

parser.add_option("--authfile", type="string",dest="AUTH_FILE", 
                  help="Authorization File name")

parser.add_option("--vmname1", type="string",dest="VMNAME1", 
                  help="VM name who not migrate")

parser.add_option("--vmname2", type="string", dest="VMNAME2", 
                  help="VM name that may be migratad")

parser.add_option("-d", "--debug", type="int",dest="DEBUGOPT",
                  help="Print debug information")

(options, args) = parser.parse_args()

if options.AUTH_FILE == "" or not options.AUTH_FILE:
    parser.error("incorrect number of arguments")
    sys.exit(1)

if options.VMNAME1 == "" or not options.VMNAME1:
    parser.error("incorrect number of arguments")
    sys.exit(1)

if options.VMNAME2 == "" or not options.VMNAME2:
    parser.error("incorrect number of arguments")
    sys.exit(1)

AUTH_FILE = options.AUTH_FILE
VMNAME1 = options.VMNAME1
VMNAME2 = options.VMNAME2

if options.DEBUGOPT:
    if type( options.DEBUGOPT ) == int:
        DEBUG = int( options.DEBUGOPT )
else:
    DEBUG = 0

if( DEBUG > 0 ):
    print "Authorization filename: '" + AUTH_FILE + "'"
    print "VM1: '" + VMNAME1 + "'"
    print "VM2: '" + VMNAME2 + "' (migratable)"

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

# connect to engine
try:
    api = None
    api = API(ENGINE_CONN, insecure=True, username=SUSERNAME, password=SPASSWORD)
    if( DEBUG > 0):
        print 'Connection established to the engine: ' + ENGINE_CONN
    
    # check if VMs exists
    EXIT_ON = 'GET_VM'
    
    vm1 = api.vms.get(name=VMNAME1)
    if vm1 == None:
        print "VM: '" + VMNAME1 + "' doesn't exist... Exit"
        sys.exit(1)
    vm2 = api.vms.get(name=VMNAME2)
    if vm2 == None:
        if( DEBUG > 0 ):
            print "VM: '" + VMNAME2 + "' doesn't exist... Exit"
        sys.exit(1)
    
    # check if VM is not the same
    if VMNAME1 == VMNAME2:
        print ( "vmname1 and vmname2 parameters are equals (%s)...Exit" %( VMNAME1 ) )
        sys.exit(1)
    
    # check if VMs are up
    EXIT_ON = 'GET_VM_STAT'
    
    vm1stat = vm1.get_status()
    vm2stat = vm2.get_status()
    
    if vm1stat.state == 'up' and vm2stat.state == 'up':
        if( DEBUG > 0):
            print ( "VM %s and VM %s are up" %( VMNAME1, VMNAME2 ) )
    else:
        print "VM not UP... Exit"
        sys.exit(0)
    
    # check if VMs are on the same host
    EXIT_ON = 'GET_VM_HOST'
    
    vm1host = vm1.get_host()
    if ( DEBUG > 0 ):
        print ( "VM %s running on %s" %( VMNAME1, vm1host.get_id() ) )
    
    vm2host = vm2.get_host()
    if ( DEBUG > 0 ):
        print ( "VM %s running on %s" %( VMNAME2, vm2host.get_id() ) )
    
    EXIT_ON = 'CHECK_HOST'
    if vm1host.get_id() == vm2host.get_id():
        print "Migrating " + VMNAME2
        try:
            #FIXME: check if vm has fixed host and only manual migration
            vm2.migrate()
            #FIXME: make sleeptime an optional parameter
            sleep(5)
        except Exception,e: 
            if e.status == 409:
                print ( "VM %s probably has running on specific host with only allow manual migration, or disallow migration..." 
                        %(VMNAME2) )
            else:
                print str(e)
    else:
        if ( DEBUG > 0 ):
            print "It's not necessary to migrate " + VMNAME2
except:
    if EXIT_ON == '':
        print 'Error: Connection failed to server: ' + ENGINE_CONN
    elif EXIT_ON == 'GET_VM':
        if( DEBUG > 0 ):
            print "Error on getting vm stat, probably doesn't exist and this error could be ignored"
    else:
        print 'Error on ' + EXIT_ON
finally:
    if api != None:
        api.disconnect()