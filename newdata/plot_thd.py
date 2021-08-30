import matplotlib.pyplot as plt
import numpy
from pathlib import Path

filename=input('Please enter filename  :')
nameoffile=Path(filename).stem + '.png'

freq, A  = numpy.genfromtxt(filename,unpack=True,usecols=range(2))

plt.plot(freq, A, color='r', marker='o', linestyle = 'None', label = "Channel A")
#plt.errorbar(freq, 10**(-A/10.0), color='r', marker='o', label = "Channel A")
#plt.plot(freq, B, 'gx',label = "Channel B")
#plt.plot(freq, C, 'b+',label = "Channel C")
#plt.plot(freq, D, 'y*',label = "Channel D")
plt.grid()
plt.xlabel('Frequency (MHz)')
plt.ylabel('THD (dB)')
plt.ylim([-24, -28])
plt.title('Frequency response for SN14 ADC board\n Carrier at Full Scale Power')

plt.legend()
#plt.show()
plt.savefig(nameoffile)
