#
# $Id: SonarPulse.py 18 2014-10-06 13:23:37Z ggx $
#

#Library import
import sys
import time
import ipaddress
import subprocess
import re
import random
from datetime import datetime
from LISPTools import LIG


PulseRevision = "$Revision: 18 $"
MaxFileTry = 10000 # Max Number of Re-tries when too many files are open

######
# Pulse Target Class
#
class PulseTarget (object):
    
    def __init__(self, host=None, timeid=None, eid=None, mr=None, logdir=None, ligtimeout=None, ligmaxtries=None, ligsrcaddress=None):
        self.host = host
        self.timeid = timeid
        self.eid = eid
        self.mr = mr
        self.logdir = logdir
        self.ligto = ligtimeout
        self.ligmaxt = ligmaxtries
        self.ligsrc = ligsrcaddress
    
    def __str__(self):
        return 'host= ' + str(self.host) + ' timeid= ' + str(self.timeid) + ' eid= ' + str(self.eid) + ' mrlist= ' + str(self.mr) + ' logdir= ' + str(self.logdir) + ' ligto= ' + str(self.ligto) + ' ligmaxt= ' + str(self.ligmaxt) + ' ligsrcaddr= ' + str(self.ligsrc)




#####
# Default Call
def Pulse(tgt):

    return BasicPulse(tgt)

# Function performing the actualy measurment
# Input: PulseTarget Class
# Output:
#       Return an error message on error, None otherwise.
#       Results written in target.logdir/EIDv[4|6]-A_B_C_D.log
#

def BasicPulse(target):
    
    
    LogFile = target.logdir + 'EIDv' + str(target.eid.version) + \
                '-' + str(target.eid).replace('.','_').replace(':','_') + \
                '-MRv' + str(target.mr.version) + \
                '-' + str(target.mr).replace('.','_').replace(':','_') + '.log'

    FTryCount = 0
        #while True:

    try:
        F = open( LogFile, "a" )

    except IOError as err:
        return 'Critical I/O Error:' + str(err) + ' (' + LogFile + ')'

    F.write('\n---PulseID-<' + str(target.timeid) + '>-' + \
            '---Host-<' + str(target.host) + '>-' + \
            '---EID-<' + str(target.eid) + '>-' + \
            '---MR-<' + str(target.mr) + '>-' + \
            '\n')

    F.write('TimeStamp\t= ' + str(target.timeid) +' \t[' + \
            datetime.fromtimestamp(target.timeid).strftime("%d.%m.%Y %H:%M:%S") + ']\n')
    F.write('Pulse \t\t= Basic\t\t['+ str(PulseRevision) + ']\n')
    F.write('Host  \t\t= ' + target.host + '\n')
    F.write('Target  EID \t= ' + str(target.eid) + '\n')
    F.write('Queried MR \t= '+ str(target.mr) + '\n')
    F.write('LIG Timeout \t= '+ str(target.ligto) + '\n')
    F.write('LIG Max Tries \t= '+ str(target.ligmaxt) +'\n')
    F.write('LIG Src Addr \t= '+ str(target.ligsrc) +'\n')

    F.write('LIG\n')

    LIGResult = LIG(target.eid, target.mr, target.ligsrc)

    F.write('|   ' + str(LIGResult))

    F.write('\n--------------------------------------------------------------->\n')

    F.close()
    return LIGResult




    # The different parameters should be configurable!
    #F.write('LIG = lig -b -d -t 3 -c 3 -m ' + str(MR) + '   ' + str(EID) + '\n')
 
 #try:
        # Here put real LIG Call
        #      LIGP = subprocess.Popen(['echo', 'HELLO!'], stdout=subprocess.PIPE)
        #except subprocess.CalledProcessError:
        #print 'Critical Error: while calling LIG function !!!'
        #sys.exit(1)
        
        #    LIGOUTPUT = LIGP.communicate()[0]
        #F.write(LIGOUTPUT)

    
    
def RLOCPulse(HOST, TS, EID, MR, LOGDIR):
    
    #print HOST + ' (' + str(ID) + ', ' + LOGDIR + '): ' + EID + ' => ' + MR
    
    try:
        IP = ipaddress.ip_address(EID)
    except ValueError:
        print '[RLOCPulse] Error No IP Address \t:' + EID
        return
    
    FILENAME = 'EIDv' + str(IP.version) + '-' + str(IP).replace('.','_').replace(':','_') + '-log.txt'

    try:
        F = open( LOGDIR + FILENAME, "a" )
    except IOError:
        print '[RLOCPulse]Critical Error \t:' + FILENAME
        return

    DATE = time.gmtime(TS)
    F.write('\n---RoundTS-<' + str(TS) + '>---HOST-<' + HOST + '>---EID-<' + str(EID) + '>---MR-<' + str(MR) + '>--->\n')
    F.write('Host =\t' + HOST + '\n') 
    F.write('Date =\t'+ str(DATE.tm_mday) + '.' + str(DATE.tm_mon) + '.' + str(DATE.tm_year) + '\n') 
    F.write('Time =\t'+ str(DATE.tm_hour) + ':' + str(DATE.tm_min) + ':' + str(DATE.tm_sec) + '\n') 
    F.write('EID =\t' + str(EID) + '\n')
    F.write('MR =\t'+ str(MR) + '\n')

# DO the LIG


    F.write('\n--------------------------------------------------------------->\n')
    F.close()
    return ##########

    # The different parameters should be configurable!
    F.write('LIG = lig -b -d -t 3 -c 3 -m ' + str(MR) + '   ' + str(EID) + '\n')
 
    try:
        # Here put real LIG Call
        LIGP = subprocess.Popen(['./lig', '-b', '-d', '-t 5', '-c 3', '-m', str(MR), str(EID)],stdout=subprocess.PIPE)
    except subprocess.CalledProcessError:
        print 'Critical Error: while calling LIG function !!!'
        sys.exit(1)
        
    LIGOUTPUT = LIGP.communicate()[0]
    LIGOUTPUTLines = LIGOUTPUT.split('\n')
    RLOC = None
    for LIGLine in LIGOUTPUTLines:
        if re.match(r"LOCATOR_\d+=", LIGLine):
            if RLOC != None:
                F.write('||LIG = lig -b -d -t 3 -c 3 -m ' + str(RLOC) + '  ' + str(EID) + '\n')
                try:
                    # Here put real LIG Call
                    LIGRLOCP = subprocess.Popen(['./lig', '-b', '-d', '-t 5', '-c 3', '-m', str(MR), str(EID)], stdout=subprocess.PIPE)
                                                 #'-b -d -t 3 -c 3 -m '+str(MR)+' '+str(EID)], stdout=subprocess.PIPE)
                except subprocess.CalledProcessError:
                    print 'Critical Error: while calling LIG function !!!'
                    sys.exit(1)
        
                LIGRLOCOUTPUT = LIGRLOCP.communicate()[0]
                LIGRLOCOUTPUTLines = LIGRLOCOUTPUT.split('\n')
                for LIGRLOCLine in LIGRLOCOUTPUTLines:
                    F.write('||' + LIGRLOCLine + '\n')
            RLOC = LIGLine.split('=')[1]
        F.write('|' + LIGLine + '\n')
    if RLOC != None:
        F.write('||LIG = lig -b -d -t 3 -c 3  -m ' + str(RLOC) + '  ' + str(EID) + '\n')
        try:
            # Here put real LIG Call
            LIGRLOCP = subprocess.Popen(['./lig', '-b', '-d', '-t 5', '-c 3', '-m', str(MR), str(EID)], stdout=subprocess.PIPE)
        except subprocess.CalledProcessError:
            print 'Critical Error: while calling LIG function !!!'
            sys.exit(1)
        
        LIGRLOCOUTPUT = LIGRLOCP.communicate()[0]
        LIGRLOCOUTPUTLines = LIGRLOCOUTPUT.split('\n')
        for LIGRLOCLine in LIGRLOCOUTPUTLines:
            F.write('||' + LIGRLOCLine + '\n')

    F.write('\n--------------------------------------------------------------->\n')
    F.close()
    
    
    
    