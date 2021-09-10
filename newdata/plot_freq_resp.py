import matplotlib.pyplot as plt
import numpy
from scipy import interpolate
from pathlib import Path

def f(x):
    #Compute power from coarse table with cubic spline interpolation
    meas_freq, meas_power = numpy.genfromtxt('cable_loss.txt',unpack=True,usecols=range(2))
    coeff = interpolate.splrep(meas_freq, meas_power)
    power = interpolate.splev(x, coeff)
    return power

filename=input("Name of text file    :")
#freq, A, B, C, D = numpy.genfromtxt(filename,unpack=True,usecols=(0,1,3,5,7))
freq, D = numpy.genfromtxt(filename,unpack=True,usecols=(0,1))
nameoffile=Path(filename).stem + '.png'

#0.11 is Vrms for this ADC
#A_V = (A/5.3)*0.11
#A_pow = 10.0*numpy.log10(A_V*A_V*1000.0/50.0)
#B_V = (B/5.3)*0.11
#B_pow = 10.0*numpy.log10(B_V*B_V*1000.0/50.0)
#C_V = (C/5.3)*0.11
#C_pow = 10.0*numpy.log10(C_V*C_V*1000.0/50.0)
D_V = (D/5.3)*0.11
D_pow = 10.0*numpy.log10(D_V*D_V*1000.0/50.0) + 6.0

comp=numpy.zeros(len(freq))
D_pow_comp=numpy.zeros(len(freq))
for i in range(len(freq)):
    comp[i]=f(freq[i])
for i in range(len(freq)):
#    A_pow[i] = A_pow[i] + comp[i] +12.1
#    B_pow[i] = B_pow[i] + comp[i] +12.1
#    C_pow[i] = C_pow[i] + comp[i] +12.1
    D_pow_comp[i] = D_pow[i] + comp[i] 

#plt.plot(freq, A_pow, 'ro',label = "Channel A")
#plt.plot(freq, B_pow, 'gx',label = "Channel B")
#plt.plot(freq, C_pow, 'b+',label = "Channel C")
plt.plot(freq, D_pow, 'y*', label = "Channel D Uncorrected")
plt.plot(freq, D_pow_comp, 'b*', label = "Channel D Corrected")
plt.grid()
plt.xlim([0, 8000])
plt.ylim([-4, 0])
plt.xlabel('Frequency (MHz)')
plt.ylabel('Power (dBm)')
plt.title('Frequency response for SN14 ADC board')

plt.legend()
#plt.show()
plt.savefig(nameoffile)
