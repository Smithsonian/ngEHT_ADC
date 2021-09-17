import matplotlib.pyplot as plt
import numpy
from scipy import interpolate
from pathlib import Path


freq =  numpy.linspace(200,16000,200,endpoint=True)
meas_freq, meas_power = numpy.genfromtxt('cable_loss.txt',unpack=True,usecols=range(2))
coeff = interpolate.splrep(meas_freq, meas_power)
power=numpy.zeros(len(freq))
for i in range(len(freq)):
    power[i] = interpolate.splev(freq[i],coeff)
#plt.plot(freq, power, 'g', label = "Spline fit")
plt.plot(meas_freq, -meas_power, 'r*',label = "Measured Cable Loss")
plt.grid()
plt.xlabel('Frequency (MHz)')
plt.ylabel('Power (dBm)')
plt.xlim([0,8000])
plt.title('Cable loss ')

plt.legend()
plt.show()
#plt.savefig(nameoffile)
