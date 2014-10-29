#!/usr/bin/python
#
# $Id: LISP-Sonar.py 18 2014-10-06 13:23:37Z ggx $
#

# -------------------------------Important Marks-------------------------------
# Surprisingly, we found that when manually executing the current Python script,
# the point symbol in file path is recognized,but not recognized when called via NEPI !!!
# Therefore, we should cover this issue replacing explicitly point symbol
# (in file path with current directory)

# Also, it is supposed to verify the existence of file path in JSON file.
# -------------------------------End of Important Marks-------------------------


#Library import
import subprocess
import socket
import os
import sys
import time
import random
import threading
import json
import Queue
import ipaddress
import resource
from jsoncomment import JsonComment

#Custom import
from SonarPulse import Pulse, PulseTarget

#-------------------------------------------------------------------
# Variables and Setting
#

#Error Exit Value
ERR = 1

Revision = "$Revision: 18 $"

# Define Default Configuration File
# Note that avoiding to use point symbol(meaning current directory in this context) in file
# path to assure the portability(we found Python scripts called by NEPI do not recognize this
# symbol)
# Refer to https://infohost.nmt.edu/tcc/help/pubs/python/web/new-str-format.html to
# get more information about Python string format's usage.
CURRENTDIR = os.path.dirname(os.path.realpath(__file__))+'/' # for example : /Users/qipengsong/Documents/First_LISP_measurement
ConfigFile = '{0}LISP-Sonar-Config.json'.format(CURRENTDIR)


#-------------------------------------------------------------------
# SubRoutines
#

######
# Logs Directory & Files Verification
#
def BootstrapFilesCheck(TimeStamp):

    #Check if the root log directory exists, if not create it.
    itexists = os.path.isdir(LogRootDirectory)
    if itexists == False :
        try:
            os.makedirs(LogRootDirectory)
        except os.error:
            print '=====> Critical Error: Creating ' + LogRootDirectory
            sys.exit(ERR)
        print '\tRoot Log Dir. [Created]\t: ' + LogRootDirectory

    else:
        print '\tRoot Log Dir.  [Found]\t: ' + LogRootDirectory

    #Get Date to check/create date-based directory tree
    rundate = time.gmtime(TimeStamp)
    DateDirectory = str(rundate.tm_year) + '/' + str(rundate.tm_mon) + '/' + str(rundate.tm_mday) +'/'

    #Check if the date-based sub-directory exists, if not create it.
    itexists = os.path.isdir(LogRootDirectory + DateDirectory)
    if itexists == False :
        try:
            os.makedirs(LogRootDirectory + DateDirectory)
        except os.error:
            print '=====> Critical Error: Creating ' + LogRootDirectory + DateDirectory
            sys.exit(ERR)
        print '\tDate Directory [Created]: ' + LogRootDirectory + DateDirectory

    else:
        print '\tDate Directory [Found]\t: ' + LogRootDirectory + DateDirectory

    return LogRootDirectory + DateDirectory

######
# Read a list from file shuffle the order and return it
#
def LoadList(FILE):

    try:
        F = open( FILE, "r" )
    except IOError:
        print '=====> Critical Error:' + FILE + ' Not Found!!!'
        sys.exit(ERR)

    LLIST = F.read().split('\n')
    F.close()

    if LLIST.count('') > 0:
        #If closing empty line exists remove it
        LLIST.remove('')

    # Randomize List so to not follow the same order at each experiment
    random.shuffle(LLIST)
    return LLIST



######
# Pulse Thread Class
#
class SonarThread (threading.Thread):

    def __init__(self, threadID, tname, prqueue):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = tname
        self.prqueue = prqueue


    def run(self):

        while True:
            item = self.prqueue.get()
            if item is None:
                break # End Loop and finish thread

            #print 'Thread ' + self.name + ' Working on: ' + str(item.eid) + '\n'
            Evalue = Pulse(item)
            if not (Evalue is None):
                print '\tError \t(!)\t\t: ' + str(Evalue)
                print >> sys.stderr, 'LISP-Sonar Error: ' + str(Evalue)





#-------------------------------------------------------------------
# Main
#

TimeStamp = int(time.time())

print 'LISP-Sonar \t\t\t: ' + Revision
print '\tRun \t\t\t: '+ time.strftime("%d.%m.%Y %H:%M:%S")

# Identify Machine and Date to Mark Logs
HOST = socket.gethostname()
print '\tHost Name \t\t: ' + HOST

# Read Configuration File
if (len(sys.argv) > 2):
    print '=====> Exiting! Too many arguments... \n'
    sys.exit(ERR)

if (len(sys.argv) == 2):
    #Always take the first argument as configuration file
    ConfigFile = str(sys.argv[1])

try:
    JsonFile = open(ConfigFile)

except:
    print  '=====> Exiting! Error opening configuration file: '+ConfigFile+'\n'
    sys.exit(ERR)

Cfg = json.load(JsonFile)

JsonFile.close()

try:
    # Remember to replace "CURRENTDIR" with real current directory path
    # for example, for item "DirsConfig"
    # "DirsConfig":
    # {
    #     "LogRootDirectory":"CURRENTDIR/SonarOutput/",
    #     "MRListDirectory":"CURRENTDIR",
    #     "MRListFile":"MR-Current-List.txt",
    #     "EIDListDirectory":"CURRENTDIR",
    #     "EIDListFile":"EID-Current-List.txt"
    # },

    # Replace "CURRENTDIR" with variable CURRENTDIR defined at the beginning
    LogRootDirectory = Cfg["DirsConfig"]["LogRootDirectory"].replace("$CURRENTDIR", CURRENTDIR)
    MRListDirectory = Cfg["DirsConfig"]["MRListDirectory"].replace("$CURRENTDIR", CURRENTDIR)
    MRListFile = Cfg["DirsConfig"]["MRListFile"]
    EIDListDirectory = Cfg["DirsConfig"]["EIDListDirectory"].replace("$CURRENTDIR", CURRENTDIR)
    EIDListFile = Cfg["DirsConfig"]["EIDListFile"]
    SpawnTimeGap = Cfg["ThreadSpawn"]["TimeGap"]
    SpawnRandomization = Cfg["ThreadSpawn"]["Randomization"]
    SpawnMaxThreads = Cfg["ThreadSpawn"]["MaxThreads"]
    LIGRequestTimeOut = Cfg["Lig"]["TimeOut"]
    LIGMaxRetries = Cfg["Lig"]["MaxTries"]
    LIGSrcAddr = Cfg["Lig"]["SourceAddress"]

except KeyError:
    print '=====> Exiting! Configuration Error for '+str(sys.exc_value)+' in file '+ConfigFile+'\n'
    sys.exit(ERR)


# Final directory where results of this instance will be written
InstanceDirectory = BootstrapFilesCheck(TimeStamp)

#Load and shuffle list of Map-Resolvers
MRList = LoadList(MRListDirectory + MRListFile)
print '\tMR List File \t\t: ' + MRListDirectory + MRListFile
print '\tMR Loaded \t\t: ' + str(len(MRList))

#Load and shuffle list of EID to lookup
EIDList = LoadList(EIDListDirectory + EIDListFile)
print '\tEID List File \t\t: ' + EIDListDirectory + EIDListFile
print '\tEID Loaded \t\t: ' + str(len(EIDList))

# CHeck Valid Source Address

if (LIGSrcAddr != "None"):

    try:
        LIGSrcIP = ipaddress.ip_address(LIGSrcAddr)
    except ValueError:
        print 'Not Valid Source Address: ' + LIGSrcAddr
        sys.exit(ERR)

else:

    LIGSrcIP = None

print '\tQuery Source Address \t: ' + str(LIGSrcIP)

# Spawn sonar threads
threads = []
threadID = 1

resource.setrlimit(resource.RLIMIT_NOFILE,(SpawnMaxThreads*4+256, resource.getrlimit(resource.RLIMIT_NOFILE)[1]))

PulseRequestQueue = Queue.Queue(SpawnMaxThreads)

for t in range(SpawnMaxThreads):

    # Create the pool of threads
    tName = 'Sonar Thread ' + `threadID`
    thread = SonarThread(threadID, tName, PulseRequestQueue)

    thread.start()
    threads.append(thread)
    threadID += 1

print '\tThreads [Now Working]\t: ' + str(SpawnMaxThreads) + ' [' + str(SpawnTimeGap) + ' +/- ' + str(SpawnRandomization) + ']'





for EID in EIDList:


    for MR in MRList:

        # Validate Addresses
        try:
            EIDIP = ipaddress.ip_address(EID)
        except ValueError:
            print 'Not Valid EID address: ' + str(EID)
            print >> sys.stderr, 'Not Valid EID address: ' + str(EID)
            continue

        try:
            MRIP = ipaddress.ip_address(MR)
        except ValueError:
            print 'Not Valid MR address: ' + str(MR)
            print >> sys.stderr, 'Not Valid MR address: ' + str(MR)
            continue

        # Put Metadata for Pulse Request in the queue only if
        # LIGSrcIP and MR are in the same family.

        if (LIGSrcIP and (LIGSrcIP.version != MRIP.version)):
            continue

        Target = PulseTarget(HOST, TimeStamp, EIDIP, MRIP, InstanceDirectory, LIGRequestTimeOut, LIGMaxRetries, LIGSrcIP)
        PulseRequestQueue.put(Target)

        # Let's put some more randomization just avoiding threads to trigger
        # requests at the same time
        time.sleep(SpawnTimeGap + random.uniform(-SpawnRandomization, SpawnRandomization))


for t in range(SpawnMaxThreads):
    # Signal to all Threads that no more  request to process
    PulseRequestQueue.put(None)


for t in threads:
    # Wait for all threads to end
    t.join()

seconds = int(time.time()) - TimeStamp
minutes, seconds = divmod(seconds, 60)
hours, minutes = divmod(minutes, 60)
print ('=====>  Done [Duration] \t: %s:%s:%s' % (hours, minutes, seconds))
sys.exit()

