#
# $Id:$
#

#Library import
import random
import netifaces
import ipaddress
import socket
import select
import time
import subprocess

LISPCONTROLPORT = 4342
MaxSockTry = 10000 # Max Number of Re-tries when too many sockets are open

from pylisp.packet.ip import IPv4Packet, IPv6Packet, UDPMessage
from pylisp.packet.lisp.control import EncapsulatedControlMessage, MapRequestMessage, ControlMessage


def IPversion2netifAF(IPversion):
    # Need to convert ipaddress version to netifaces address family

    if IPversion == 4:
        return netifaces.AF_INET

    if IPversion == 6:
        return netifaces.AF_INET6

    return None


def GetSrcIPAddr(AF):

    if not AF:
        return None

    AddrList = []

    for interface in netifaces.interfaces():
        if netifaces.ifaddresses(interface):
            if AF in netifaces.ifaddresses(interface):
                for ipaddr in netifaces.ifaddresses(interface)[AF]:
                    CurrentIPitem = ipaddress.ip_address(ipaddr['addr'].rsplit('%',1)[0])

                    if not CurrentIPitem.is_loopback and \
                        not CurrentIPitem.is_link_local and \
                        not CurrentIPitem.is_multicast and \
                        not CurrentIPitem.is_unspecified and \
                        not CurrentIPitem.is_reserved:
                        AddrList.append(ipaddr['addr'])


    if AddrList:
        return ipaddress.ip_address(AddrList[0]) #Just Return the first Usable IP

    else:
        return None




# Improve the portability of this method to seamlessly support Linux/FreeBSD(Including Mac OS) OS
def LIG(EID=None, MR=None, SrcIP=None, MaxReq=3, TimeOut=1, Output=None, Pcap=None):


    if EID == None:
        return 'Not Valid EID address: ' + str(EID)

    if MR == None:
        return 'Not Valid MR address: ' + str(MR)


    if SrcIP == None:

        SrcIP = GetSrcIPAddr(IPversion2netifAF(MR.version))

    if not SrcIP:
        return 'Not Valid Source Address Found!'

    # Should check if the provided source IP is actually usable, but
    # if it is not socket call will give error

    # First Open Socket so to know if we can communicate
    (SrcSockAF, SrcSockType, SrcSockProto, SrcSockCName, SrcSockAddr) = socket.getaddrinfo(str(SrcIP), None)[0]
    (MRSockAF, MRSockType, MRSockProto, MRSockCName, MRSockAddr) = socket.getaddrinfo(str(MR), LISPCONTROLPORT, 0, 0, socket.SOL_UDP)[0]

    try:
        s = socket.socket(MRSockAF, MRSockType, MRSockProto)
        SrcPort = s.getsockname()[1]

    except socket.error as err:
        return 'Sending Socket Error: ' + str(err)


    try:
        r = socket.socket(MRSockAF, MRSockType, MRSockProto)
        r.bind(('', SrcPort))

    except socket.error as err:
        r.close()
        s.close()
        return 'Receiving Socket Error: ' + str(err)


    #SONG Qipeng : KQueue/kevent is I/O mechanism under FreeBSD(including Mac OSX), and POLL is for Linux
    #SONG Qipeng : we consider the portability problem.
    if hasattr(select, "kqueue"):
        KSockQ = select.kqueue()
        KSockEvent = select.kevent(r.fileno(), filter=select.KQ_FILTER_READ, \
                                   flags=select.KQ_EV_ADD | select.KQ_EV_ENABLE | select.KQ_EV_ONESHOT)

        SentMapRequests = []

        while (len(SentMapRequests) <= MaxReq):

            # Build the map request
            nonce = ''.join([chr(random.choice(xrange(256))) for i in range(8)])
            MapRequest = MapRequestMessage(False,
                                           False,
                                           False,
                                           False,
                                           False,
                                           nonce,
                                           SrcIP,
                                           [SrcIP],
                                           [EID],
                                           None)

            # Build UDP Encap
            UDPpkt = UDPMessage(SrcPort, LISPCONTROLPORT, 0, MapRequest)
            UDPpkt.checksum = UDPpkt.calculate_checksum(SrcIP, MR)

            #Build IP Encap
            if (MRSockAF == socket.AF_INET):
                ECMPayload = IPv4Packet(ttl=64,
                                        protocol = UDPpkt.header_type,
                                        source = SrcIP,
                                        destination = MR,
                                        payload = UDPpkt)

            elif (MRSockAF == socket.AF_INET6):
                ECMPayload = IPv6Packet(next_header = UDPpkt.header_type,
                                        hop_limit = 64,
                                        source = SrcIP,
                                        destination = MR,
                                        payload=UDPpkt)

            else:
                return 'Error: AF not recognized!'

            # Build LISP Encapsulated Control Message
            ECM = EncapsulatedControlMessage(False,
                                             False,
                                             False,
                                             False,
                                             ECMPayload)

            #print 'ECM = \t\t' + bytes(ECM).encode('hex')

            try:
                print 'Sending MapRequest ' + str(len(SentMapRequests)) + ' for ' + str(EID) + ' to ' + str(MR)
                s.sendto(bytes(ECM), MRSockAddr)
                SentMapRequests.append((nonce, time.time()))

            except socket.error as err:
                KSockQ.close()
                r.close()
                s.close()
                return 'Sending Map-Request Socket Error [' + str(socket.error) +']'

            try:
                ReadEvents = KSockQ.control([KSockEvent], 1, TimeOut)
                if ReadEvents:
                    print 'Received Something .... !!!!!'
                    MapReply = r.recv(4096, socket.MSG_WAITALL)

                else:
                    print 'Received NOTHING .... !!!!!'

            except socket.error as err:
                KSockQ.close()
                r.close()
                s.close()
                return 'Receiving Map-Reply Socket Error: ' + str(err)
        KSockQ.close()


    elif hasattr(select, "epoll"):
        # The case when code runs under Linux environment
        epoll = select.epoll()
        epoll.register(r.fileno(), select.EPOLLIN)

        SentMapRequests = []

        while (len(SentMapRequests) <= MaxReq):

            # Build the map request
            nonce = ''.join([chr(random.choice(xrange(256))) for i in range(8)])
            MapRequest = MapRequestMessage(False,
                                           False,
                                           False,
                                           False,
                                           False,
                                           nonce,
                                           SrcIP,
                                           [SrcIP],
                                           [EID],
                                           None)

            # Build UDP Encap
            UDPpkt = UDPMessage(SrcPort, LISPCONTROLPORT, 0, MapRequest)
            UDPpkt.checksum = UDPpkt.calculate_checksum(SrcIP, MR)

            #Build IP Encap
            if (MRSockAF == socket.AF_INET):
                ECMPayload = IPv4Packet(ttl=64,
                                        protocol = UDPpkt.header_type,
                                        source = SrcIP,
                                        destination = MR,
                                        payload = UDPpkt)

            elif (MRSockAF == socket.AF_INET6):
                ECMPayload = IPv6Packet(next_header = UDPpkt.header_type,
                                        hop_limit = 64,
                                        source = SrcIP,
                                        destination = MR,
                                        payload=UDPpkt)

            else:
                return 'Error: AF not recognized!'

            # Build LISP Encapsulated Control Message
            ECM = EncapsulatedControlMessage(False,
                                             False,
                                             False,
                                             False,
                                             ECMPayload)

            #print 'ECM = \t\t' + bytes(ECM).encode('hex')

            try:
                print 'Sending MapRequest ' + str(len(SentMapRequests)) + ' for ' + str(EID) + ' to ' + str(MR)
                s.sendto(bytes(ECM), MRSockAddr)
                SentMapRequests.append((nonce, time.time()))

            except socket.error as err:
                epoll.unregister(r.fileno())
                epoll.close()
                r.close()
                s.close()
                return 'Sending Map-Request Socket Error [' + str(socket.error) +']'

            try:
                #ReadEvents = KSockQ.control([KSockEvent], 1, TimeOut)
                ReadEvents = epoll.poll(TimeOut)
                if ReadEvents:
                    print 'Received Something .... !!!!!'
                    MapReply = r.recv(4096, socket.MSG_WAITALL)

                else:
                    print 'Received NOTHING .... !!!!!'

            except socket.error as err:
                epoll.unregister(r.fileno())
                epoll.close()
                r.close()
                s.close()
                return 'Receiving Map-Reply Socket Error: ' + str(err)
        epoll.unregister(r.fileno())
        epoll.close()



#==============================================
    # Now decapsulate and find nonce


    r.close()
    s.close()

    return None


