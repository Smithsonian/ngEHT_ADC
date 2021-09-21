#!/usr/bin/python2.7

import socket   #for sockets
import sys  #for exit
import numpy

if __name__ == '__main__':
    from optparse import OptionParser

    p = OptionParser()
    p.set_usage('%prog [options]')
    p.set_description(__doc__)
    p.add_option('-f', '--freq', dest='freq', type='float', default=0,
        help='''Select the frequency in MHz''')
    p.add_option('-p', '--power', dest='power', type='float', default=0,
        help='''Select the power ''')
    p.add_option('-v', '--verbose', dest = 'verbose', action = 'store_true',
        help = '''Be verbose about errors.''')

    opts, args = p.parse_args(sys.argv[1:])

if not opts.freq:
    p.error('Frequency not specified')
    sys.exit()
if not opts.power:
    p.error('Power not specified')
    sys.exit()

frequency=opts.freq
power=opts.power

#if (frequency < 4 or frequency > 9.5):
#  print "Frequency not in range"
#  sys.exit()

#create an INET, STREAMing socket
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
except socket.error:
    print('Failed to create socket')
    sys.exit()

print('Socket Created')

port = 5025

remote_ip = '131.142.238.63'

#Connect to remote server
s.connect((remote_ip , port))

print('Socket Connected to ' + ' ip ' + remote_ip)

#Send some data to remote server
message = 'freq ' + str(frequency) + ' MHz\n'
print(message)

try :
    #Set the whole string
    s.sendall(message.encode())
except socket.error:
    #Send failed
    print('Send failed')
    sys.exit()

print('Message send successfully')

message = 'pow:ampl ' + str(power) + ' dBm\n'

try :
    #Set the whole string
    s.sendall(message.encode())
except socket.error:
    #Send failed
    print('Send failed')
    sys.exit()

print('Message send successfully')

message = "freq:cw?\n"

try :
    #Set the whole string
    s.sendall(message.encode())
except socket.error:
    #Send failed
    print('Send failed')
    sys.exit()

print('Frequency Query')
#Now receive data
reply = s.recv(4096)

frequency=float(reply.decode().rstrip('\n'))
formatted_frequency = "{:.3f}".format(frequency)

print("Frequency is:  " + formatted_frequency + ' Hz')

message = "pow:ampl?\n"

try :
    #Set the whole string
    s.sendall(message.encode())
except socket.error:
    #Send failed
    print('Send failed')
    sys.exit()

print('Power Query')

#Now receive data
reply = s.recv(4096)

print("Power is:  " + reply.decode().rstrip('\n') + ' dBm')

message = "OUTP ON\n"

try :
    #Set the whole string
    s.sendall(message.encode())
except socket.error:
    #Send failed
    print('Send failed')
    sys.exit()

message = "OUTP?\n"


try :
    #Set the whole string
    s.sendall(message.encode())
except socket.error:
    #Send failed
    print('Send failed')
    sys.exit()

print('RF output Status Query')

#Now receive data
reply = s.recv(4096)

status=reply.decode().rstrip('\n')
if (int(status) == 1):
   print("RF Output is: ON ") 
else:
   print("RF Output is: OFF ") 
   


