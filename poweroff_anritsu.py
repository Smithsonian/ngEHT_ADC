import pyvisa   
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
        help='''Select the power in dBm''')
    p.add_option('-v', '--verbose', dest = 'verbose', action = 'store_true',
        help = '''Be verbose about errors.''')

    opts, args = p.parse_args(sys.argv[1:])


rm = pyvisa.ResourceManager('@py')
ipaddr = 'TCPIP0::131.142.238.62::INSTR'
inst = rm.open_resource(ipaddr)
inst.write('*CLS')
inst.query('*IDN?')

#Turn output off
message='outp off'
inst.write(message)

reply=inst.query('outp?')
stat_query=int(reply.rstrip('\r\n'))
if (stat_query == 1):
    print('RF output is on')
else:
    print('RF output is off')

reply=inst.query('rosc:sour?')
print(reply)

inst.close()



