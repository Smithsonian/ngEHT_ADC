import matplotlib.pyplot as plt
import numpy
from scipy.optimize import curve_fit

def f(x, m, c):
    return m*x + c

freq, A, B, C, D = numpy.genfromtxt('freq_response_SN14.txt',skip_header=2,unpack=True,usecols=range(5))

#0.11 is Vrms for this ADC
A_V = (A/5.3)*0.11
A_pow = 10.0*numpy.log10(A_V*A_V*1000.0/50.0)
B_V = (B/5.3)*0.11
B_pow = 10.0*numpy.log10(B_V*B_V*1000.0/50.0)
C_V = (C/5.3)*0.11
C_pow = 10.0*numpy.log10(C_V*C_V*1000.0/50.0)
D_V = (D/5.3)*0.11
D_pow = 10.0*numpy.log10(D_V*D_V*1000.0/50.0)

meas_freq, meas_power = numpy.genfromtxt('cable_loss.txt',unpack=True,usecols=range(2))
popt, pcov = curve_fit(f, meas_freq, meas_power)
print("{:.2e}".format(popt[0])) 
print("{:.2e}".format(popt[1])) 

for i in range(len(freq)):
    A_pow[i] = A_pow[i] + (popt[0]*freq[i]) - popt[1]
    B_pow[i] = B_pow[i] + (popt[0]*freq[i]) - popt[1]
    C_pow[i] = C_pow[i] + (popt[0]*freq[i]) - popt[1]
    D_pow[i] = D_pow[i] + (popt[0]*freq[i]) - popt[1]

plt.plot(freq, A_pow, 'ro',label = "Channel A")
plt.plot(freq, B_pow, 'gx',label = "Channel B")
plt.plot(freq, C_pow, 'b+',label = "Channel C")
plt.plot(freq, D_pow, 'y*',label = "Channel D")
plt.grid()
plt.xlabel('Frequency (MHz)')
plt.ylabel('Power (dBm)')
plt.title('Frequency response for SN14 ADC board')

plt.legend()
plt.show()
plt.savefig('Freq_response_SN14.png')
