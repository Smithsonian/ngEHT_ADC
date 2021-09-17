import matplotlib.pyplot as plt
import numpy
from pathlib import Path

filename=input('Please enter filename  :')
nameoffile1=Path(filename).stem + '_SINAD_ENOB.png'
nameoffile2=Path(filename).stem + '_SFDR.png'
nameoffile3=Path(filename).stem + '_THD.png'

freq, sinad, sfdr, thd, enob  = numpy.genfromtxt(filename,unpack=True,usecols=range(5))

fig, ax = plt.subplots()
#plt.plot(freq, B, 'gx',label = "Channel B")
#plt.plot(freq, C, 'b+',label = "Channel C")
#plt.plot(freq, D, 'y*',label = "Channel D")
ax.set_xlabel('Frequency (MHz)')
ax.set_ylabel('SINAD (dB)')
ax.set_ylim([-18, -22])
ax.grid()
ax2=ax.twinx()
ax.plot(freq, sinad, color='r', marker='o', linestyle = 'None', label='Channel A')
ax2.plot(freq, enob, color='g', marker='+', linestyle = 'None', label='Channel A')
ax2.set_ylabel('ENOB (Bits)')
ax2.grid()
ax2.set_ylim([2, 6])

plt.title('Frequency response for SN14 ADC board\n Carrier at Full Scale Power')

#plt.legend()
#plt.show()
fig.savefig(nameoffile1)

plt.clf()
plt.plot(freq, sfdr, color='r', marker='o', linestyle = 'None', label='Channel A')
plt.xlabel('Frequency (MHz)')
plt.ylabel('SFDR (dB)')
plt.ylim([-26, -30])
plt.grid()
plt.title('Frequency response for SN14 ADC board\n Carrier at Full Scale Power')
plt.savefig(nameoffile2)

plt.clf()
plt.plot(freq, thd, color='r', marker='o', linestyle = 'None', label='Channel A')
plt.xlabel('Frequency (MHz)')
plt.ylabel('THD (dB)')
plt.ylim([-26, -30])
plt.grid()
plt.title('Frequency response for SN14 ADC board\n Carrier at Full Scale Power')
plt.savefig(nameoffile3)
