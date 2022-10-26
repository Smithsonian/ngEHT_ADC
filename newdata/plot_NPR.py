import matplotlib.pyplot as plt
import matplotlib
matplotlib.rcParams.update({'font.size': 14})
import numpy
from pathlib import Path
from scipy.interpolate import interp1d
from scipy.optimize import fmin


#Theoretical NPR values

roottwopi = 2.50662827463
roottwobypi = 0.797884560803

loadingFactors = numpy.array([])
NPRs = numpy.array([])
Nbit=4

for lf in numpy.arange(-40,2,0.1):
        k = 10.0**(-lf/20.)

        expfact = numpy.exp(-k*k/2.0)

        denom1 = (k*k + 2.0)
        denom2 = denom1*(k*k + 4.0)
        denom3 = denom2*(k*k + 6.0)
        denom4 = denom3*(k*k + 8.0)
        denom5 = denom4*(k*k + 10.0)
        sum = 1.0-1.0/denom1+1.0/denom2-5.0/denom3+9.0/denom4-129.0/denom5
        oneMinusKterm = (1.0/(k*roottwopi))*expfact * sum

        term1 = k*k/(3.0*2.0**(2.0*Nbit))
        term2 = 2.0*(k*k+1.0)*oneMinusKterm

        NtbySigmaSquare = term1 + term2 - k*roottwobypi*expfact

        NPR = -10.0*numpy.log10(NtbySigmaSquare)

        loadingFactors = numpy.append(loadingFactors,lf)

        NPRs = numpy.append(NPRs,NPR)
        maxNPRs = numpy.amax(NPRs)
        maxind = numpy.where(NPRs == numpy.amax(NPRs))
        maxLF = loadingFactors[maxind]
print(maxNPRs,maxLF)

freq=input('Notch frequency    :')
figname='NPR_' + str(freq) + '.png'
filename='NPR_0_' + str(freq) + '.txt'
level0, NPR0, rms0  = numpy.genfromtxt(filename,unpack=True,usecols=range(3))
filename='NPR_1_' + str(freq) + '.txt'
level1, NPR1, rms1  = numpy.genfromtxt(filename,unpack=True,usecols=range(3))
filename='NPR_2_' + str(freq) + '.txt'
level2, NPR2, rms2  = numpy.genfromtxt(filename,unpack=True,usecols=range(3))
filename='NPR_3_' + str(freq) + '.txt'
level3, NPR3, rms3  = numpy.genfromtxt(filename,unpack=True,usecols=range(3))

V0 = 7.5 # in dBm units
k0 = 24 * [0.0]
lf0 = 24 * [0.0]
k1 = 24 * [0.0]
lf1 = 24 * [0.0]
k2 = 24 * [0.0]
lf2 = 24 * [0.0]
k3 = 24 * [0.0]
lf3 = 24 * [0.0]
for i in range(len(level0)):
    k0[i]=V0/rms0[i]
    k1[i]=V0/rms1[i]
    k2[i]=V0/rms2[i]
    k3[i]=V0/rms3[i]
    lf0[i]=-20*numpy.log10(k0[i])
    lf1[i]=-20*numpy.log10(k1[i])
    lf2[i]=-20*numpy.log10(k2[i])
    lf3[i]=-20*numpy.log10(k3[i])

fit0 = interp1d(lf0, NPR0, kind='cubic')
fit0_neg = interp1d(lf0, -NPR0, kind='cubic')
lf0_max=fmin(fit0_neg,-8)

fit1 = interp1d(lf1, NPR1, kind='cubic')
fit1_neg = interp1d(lf1, -NPR1, kind='cubic')
lf1_max=fmin(fit1_neg,-8)

fit2 = interp1d(lf2, NPR2, kind='cubic')
fit2_neg = interp1d(lf2, -NPR2, kind='cubic')
lf2_max=fmin(fit2_neg,-8)

fit3 = interp1d(lf3, NPR3, kind='cubic')
fit3_neg = interp1d(lf3, -NPR3, kind='cubic')
lf3_max=fmin(fit3_neg,-8)

fig, ax = plt.subplots()
ax.set_xlabel('Loading factor (dB)')
ax.set_ylabel('NPR (dB)')
ax.set_ylim([0, 30])
ax.set_xlim([-25, 0])
ax.grid()
ax.plot(loadingFactors, NPRs, color='k', marker='None', linestyle = 'solid', label='Channel B')

ax.plot(lf0, NPR0, color='r', marker='o', linestyle = 'None', label='Channel A')
ax.plot(lf0, fit0(lf0), color='g', marker='None', linestyle = 'solid', label='Channel A')
ax.plot(lf0_max, fit0(lf0_max), color='k', marker='*', linestyle = 'None', label='Channel A')
ax.plot(lf1, NPR1, color='r', marker='o', linestyle = 'None', label='Channel B')
ax.plot(lf1, fit1(lf1), color='g', marker='None', linestyle = 'solid', label='Channel B')
ax.plot(lf1_max, fit1(lf1_max), color='k', marker='*', linestyle = 'None', label='Channel B')
ax.plot(lf2, NPR2, color='r', marker='o', linestyle = 'None', label='Channel C')
ax.plot(lf2, fit2(lf2), color='g', marker='None', linestyle = 'solid', label='Channel C')
ax.plot(lf2_max, fit2(lf2_max), color='k', marker='*', linestyle = 'None', label='Channel C')
ax.plot(lf3, NPR3, color='r', marker='o', linestyle = 'None', label='Channel D')
ax.plot(lf3, fit3(lf3), color='g', marker='None', linestyle = 'solid', label='Channel D')
ax.plot(lf3_max, fit3(lf3_max), color='k', marker='*', linestyle = 'None', label='Channel D')

ax.text(-24.8,27.5,'Fitted Max LF, NPR = {0:1.2f}, {1:1.2f}'.format(float(lf0_max), float(fit0(lf0_max))))
ax.text(-24.8,25.0,'Fitted Max LF, NPR = {0:1.2f}, {1:1.2f}'.format(float(lf1_max), float(fit0(lf1_max))))
ax.text(-24.8,22.5,'Fitted Max LF, NPR = {0:1.2f}, {1:1.2f}'.format(float(lf2_max), float(fit0(lf2_max))))
ax.text(-24.8,20.0,'Fitted Max LF, NPR = {0:1.2f}, {1:1.2f}'.format(float(lf2_max), float(fit0(lf3_max))))

ax.axvline(-8.2)
ax.text(-8.0,20,'{0:1.2f}, {1:1.2f}'.format(float(maxLF), float(maxNPRs),rotation=0))

ax.set_title("Theoretical and measured NPR curves for Channels A, B, C and D;\n SN14, Notch Frequency = 6.025 GHz")

ax.legend(['Theoretical','data','fit','max'], loc='best', numpoints=1)
fig.set_size_inches(10, 6)
plt.savefig(figname)
#plt.show()

