import pyvisa   
import sys  #for exit
import numpy
from scipy import interpolate
import time


if __name__ == '__main__':
   


    rm = pyvisa.ResourceManager('@py')
    ipaddr = 'TCPIP0::131.142.238.62::INSTR'
    inst = rm.open_resource(ipaddr)
    inst.write('*CLS')
    inst.query('*IDN?')

    #Compute power from coarse table with cubic spline interpolation
    meas_freq, meas_power = numpy.genfromtxt('freq_power.txt',unpack=True,usecols=range(2))
    meas_power=meas_power+5.9 #added a 6 dB pad at the RF input
    coeff = interpolate.splrep(meas_freq, meas_power)


    for i in range (40):
        frequency = 200*(i+1)
        #Set frequency
        message='freq ' + str(frequency) + ' MHz'
        inst.write(message)

        power = interpolate.splev(frequency, coeff)
        formatted_power="{:.2f}".format(power)

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
        time.sleep(10)

    inst.close()



