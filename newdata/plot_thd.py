import matplotlib.pyplot as plt
import numpy


freq, A  = numpy.genfromtxt('thd_SN14_ch0.txt',skip_header=2,unpack=True,usecols=range(2))

plt.plot(freq, A, color='r', marker='o', linestyle = 'None', label = "Channel A")
#plt.errorbar(freq, 10**(-A/10.0), color='r', marker='o', label = "Channel A")
#plt.plot(freq, B, 'gx',label = "Channel B")
#plt.plot(freq, C, 'b+',label = "Channel C")
#plt.plot(freq, D, 'y*',label = "Channel D")
plt.grid()
plt.xlabel('Frequency (MHz)')
plt.ylabel('THD (dB)')
plt.ylim([-20, -30])
plt.title('Frequency response for SN14 ADC board\n Carrier at Full Scale Power')

plt.legend()
#plt.show()
plt.savefig('THD_SN14_ch0.png')
