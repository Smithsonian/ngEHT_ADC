import sys  #for exit
import numpy
import socket
from scipy import interpolate

def open_sg():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    except socket.error:
        print('Failed to create socket')
        sys.exit()
    
    port = 5025;

    remote_ip = '131.142.238.63'

    #Connect to remote server
    s.connect((remote_ip , port))
    return s


def set_freq(frequency,s):

    if ((frequency < 100) or (frequency > 8192)):
        print('CW Frequency out of range')
        sys.exit()
    
    #Compute power from coarse table with cubic spline interpolation
    meas_freq, meas_power = numpy.genfromtxt('freq_power.txt',unpack=True,usecols=range(2))
    meas_power=meas_power+5.9 #added a 6 dB pad at the RF input
    coeff = interpolate.splrep(meas_freq, meas_power)
    power = interpolate.splev(frequency, coeff)
    formatted_power="{:.2f}".format(power)

    #Set frequency
    message='freq ' + str(frequency) + ' MHz\n'
    s.sendall(message.encode())

    #Set power
    message='pow ' + str(formatted_power) + ' dBm\n'
    s.sendall(message.encode())

    message='pow:ampl?\n'
    s.sendall(message.encode())
    reply=s.recv(4096)
    pow_query=reply.decode().rstrip('\r\n')
    print("Power is:  " + pow_query + ' dBm')

    message='freq:cw?\n'
    s.sendall(message.encode())
    reply=s.recv(4096)
    freq_query=float(reply.decode().rstrip('\r\n'))

    formatted_frequency = "{:.10f}".format(freq_query)

    print("Frequency is:  " + formatted_frequency + ' Hz')

    #Turn output on
    message='outp on\n'
    s.sendall(message.encode())
    

    message='outp?\n'
    s.sendall(message.encode())
    
    reply=s.recv(4096)
    stat_query=int(reply.decode().rstrip('\r\n'))
    if (stat_query == 1):
        print('RF output is on')
    else:
        print('RF output is off')

    return formatted_power

def set_freq_only(frequency,s):

    #try:
    #    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    #except socket.error:
    #    print('Failed to create socket')
    #    sys.exit()
    if ((frequency < 100) or (frequency > 16000)):
        print('CW Frequency out of range')
        sys.exit()
   # 
    #port = 5025;

    #remote_ip = '131.142.238.63'
#
#    Connect to remote server
    #s.connect((remote_ip , port))

    #Set frequency
    message='freq ' + str(frequency) + ' MHz\n'
    s.sendall(message.encode())
    
    message='freq:cw?\n'
    s.sendall(message.encode())
    
    reply=s.recv(4096)
    freq_query=float(reply.decode().rstrip('\r\n'))


    formatted_frequency = "{:.10f}".format(freq_query)

    print("Frequency is:  " + formatted_frequency + ' Hz')

    message='outp?\n'
    s.sendall(message.encode())
    
    reply=s.recv(4096)
    stat_query=int(reply.decode().rstrip('\r\n'))
    if (stat_query == 1):
        print('RF output is on')
    else:
        print('RF output is off')



def set_power(newpower,s):
    #Set power
    message='pow ' + str(newpower) + ' dBm\n'
    s.sendall(message.encode())
    
    message='pow:ampl?\n'
    s.sendall(message.encode())
    
    reply=s.recv(4096)
    pow_query=reply.decode().rstrip('\r\n')
    print("Power is:  " + pow_query + ' dBm')

def close_sg(s):
    s.close()



