import matplotlib.pyplot as plt
import numpy
from pathlib import Path

filename=input('Please enter filename  :')
nameoffile1=Path(filename).stem + '_SINAD_ENOB.png'
nameoffile2=Path(filename).stem + '_SFDR.png'

freq, A, B, C  = numpy.genfromtxt(filename,unpack=True,usecols=range(4))

fig, ax = plt.subplots()
#plt.plot(freq, B, 'gx',label = "Channel B")
#plt.plot(freq, C, 'b+',label = "Channel C")
#plt.plot(freq, D, 'y*',label = "Channel D")
ax.set_xlabel('Frequency (MHz)')
ax.set_ylabel('SINAD (dB)')
ax.set_ylim([-18, -22])
ax2=ax.twinx()
ax.plot(freq, A, color='r', marker='o', linestyle = 'None', label='Channel A')
ax2.plot(freq, C, color='g', marker='+', linestyle = 'None', label='Channel A')
ax2.set_ylabel('ENOB (Bits)')
ax2.set_ylim([2, 5])

plt.title('Frequency response for SN14 ADC board\n Carrier at Full Scale Power')

#plt.legend()
#plt.show()
fig.savefig(nameoffile1)

plt.clf()
plt.plot(freq, B, color='r', marker='o', linestyle = 'None', label='Channel A')
plt.xlabel('Frequency (MHz)')
plt.ylabel('SINAD (dB)')
plt.ylim([-24, -30])
plt.title('Frequency response for SN14 ADC board\n Carrier at Full Scale Power')
plt.savefig(nameoffile2)
