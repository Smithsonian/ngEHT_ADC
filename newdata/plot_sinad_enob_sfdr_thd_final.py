import matplotlib.pyplot as plt
import matplotlib 
matplotlib.rcParams.update({'font.size': 12})
import numpy
from pathlib import Path

filename=input('Please enter Ch0 ADC filename  :')
freq0, sinad0, sfdr0, thd0, enob0  = numpy.genfromtxt(filename,unpack=True,usecols=range(5))
filename=input('Please enter Ch1 ADC filename  :')
freq1, sinad1, sfdr1, thd1, enob1  = numpy.genfromtxt(filename,unpack=True,usecols=range(5))
filename=input('Please enter Ch2 ADC filename  :')
freq2, sinad2, sfdr2, thd2, enob2  = numpy.genfromtxt(filename,unpack=True,usecols=range(5))
filename=input('Please enter Ch3 ADC filename  :')
freq3, sinad3, sfdr3, thd3, enob3  = numpy.genfromtxt(filename,unpack=True,usecols=range(5))

nameoffile1='Ch0123' + '_SINAD_ENOB_New.png'
nameoffile2='Ch0123' + '_SFDR_New.png'
nameoffile3='Ch0123' + '_THD_New.png'


fig, ax = plt.subplots()
ax.set_xlabel('Frequency (MHz)')
ax.set_ylabel('SINAD (dB)',color='r')
ax.set_ylim([17.5, 22])
ax.grid()
ax2=ax.twinx()
ax.plot(freq0, -sinad0, color='r', marker='o', linestyle = 'None', label='Channel A')
ax.plot(freq0, -sinad1, color='r', marker='+', linestyle = 'None', label='Channel B')
ax.plot(freq0, -sinad2, color='r', marker='*', linestyle = 'None', label='Channel C')
ax.plot(freq0, -sinad3, color='r', marker='x', linestyle = 'None', label='Channel D')
ax.legend(loc='lower left')
ax2.legend(loc='lower right')
ax.tick_params(axis='y', colors='r')
ax2.plot(freq0, enob0, color='g', marker='o', linestyle = 'None', label='Channel A')
ax2.plot(freq0, enob1, color='g', marker='+', linestyle = 'None', label='Channel B')
ax2.plot(freq0, enob2, color='g', marker='*', linestyle = 'None', label='Channel C')
ax2.plot(freq0, enob3, color='g', marker='x', linestyle = 'None', label='Channel D')
ax2.set_ylabel('ENOB (Bits)',color='g')
ax2.grid()
ax2.set_ylim([1.5, 6])
ax2.legend(loc='lower right')
ax2.tick_params(axis='y', colors='g')

plt.title('Frequency response for SN14 ADC board\n Carrier at Full Scale Power')

#plt.legend()
#plt.show()
fig.savefig(nameoffile1)

plt.clf()
plt.plot(freq0, sfdr0, color='r', marker='o', linestyle = 'None', label='Channel A')
plt.plot(freq0, sfdr1, color='g', marker='+', linestyle = 'None', label='Channel B')
plt.plot(freq0, sfdr2, color='b', marker='*', linestyle = 'None', label='Channel C')
plt.plot(freq0, sfdr3, color='y', marker='x', linestyle = 'None', label='Channel D')
plt.xlabel('Frequency (MHz)')
plt.ylabel('SFDR (dB)')
plt.ylim([-25, -35])
plt.grid()
plt.title('Frequency response for SN14 ADC board\n Carrier at Full Scale Power')
plt.legend()
plt.savefig(nameoffile2)

plt.clf()
plt.plot(freq0, thd0, color='r', marker='o', linestyle = 'None', label='Channel A')
plt.plot(freq0, thd1, color='g', marker='+', linestyle = 'None', label='Channel B')
plt.plot(freq0, thd2, color='b', marker='*', linestyle = 'None', label='Channel C')
plt.plot(freq0, thd3, color='y', marker='x', linestyle = 'None', label='Channel D')
plt.xlabel('Frequency (MHz)')
plt.ylabel('THD (dB)')
plt.ylim([-24, -34])
plt.grid()
plt.legend()
plt.title('Frequency response for SN14 ADC board\n Carrier at Full Scale Power')
plt.savefig(nameoffile3)
