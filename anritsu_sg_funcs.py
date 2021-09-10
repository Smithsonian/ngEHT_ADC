import pyvisa   
import sys  #for exit
import numpy
from scipy import interpolate

def open_sg():
    rm = pyvisa.ResourceManager('@py')
    ipaddr = 'TCPIP0::131.142.238.62::INSTR'
    inst = rm.open_resource(ipaddr)
    inst.write('*CLS')
    inst.query('*IDN?')
    return inst

def set_freq(frequency,inst):

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
    message='freq ' + str(frequency) + ' MHz'
    inst.write(message)

    #Set power
    message='pow ' + str(formatted_power) + ' dBm'
    inst.write(message)

    reply=inst.query('pow?')
    pow_query=reply.rstrip('\r\n')
    print("Power is:  " + pow_query + ' dBm')

    reply=inst.query('freq?')
    freq_query=float(reply.rstrip('\r\n'))

    formatted_frequency = "{:.10f}".format(freq_query)

    print("Frequency is:  " + formatted_frequency + ' Hz')

    #Turn output on
    message='outp on'
    inst.write(message)

    reply=inst.query('outp?')
    stat_query=int(reply.rstrip('\r\n'))
    if (stat_query == 1):
        print('RF output is on')
    else:
        print('RF output is off')

    reply=inst.query('rosc:sour?')
    print(reply)
    return formatted_power

def set_freq_only(frequency,inst):

    if ((frequency < 100) or (frequency > 16000)):
        print('CW Frequency out of range')
        sys.exit()
    
    #Set frequency
    message='freq ' + str(frequency) + ' MHz'
    inst.write(message)

    reply=inst.query('freq?')
    freq_query=float(reply.rstrip('\r\n'))

    formatted_frequency = "{:.10f}".format(freq_query)

    print("Frequency is:  " + formatted_frequency + ' Hz')

    reply=inst.query('outp?')
    stat_query=int(reply.rstrip('\r\n'))
    if (stat_query == 1):
        print('RF output is on')
    else:
        print('RF output is off')

    reply=inst.query('rosc:sour?')
    print(reply)

def set_power(newpower,inst):
    #Set power
    message='pow ' + str(newpower) + ' dBm'
    inst.write(message)
    
    reply=inst.query('pow?')
    pow_query=reply.rstrip('\r\n')
    print("Power is:  " + pow_query + ' dBm')

def close_sg(inst):
    inst.close()



