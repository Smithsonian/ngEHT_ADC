import sys
import os
import time
#import address as a
import constants as c
#import board_comm
from columnar import columnar
from scipy.fftpack import fft, rfft
import matplotlib.pyplot as plt
from matplotlib.mlab import psd, detrend_mean
import numpy as np
from numpy import math
#import synth_tools as synth
from math import pi, sqrt, sin, atan2
from scipy import signal

#Catchall that takes a set of frequency data, does psd, histogram, enob, sinad, and sfdr, and prints
def do_analysis(allrundata, results_dir):

    results = []
    histdata = []
    for run in allrundata:

        hist = []
        sample = []
        samp = runs.samplingfreq
        sig = runs.signalfreq
        bd = run.board
        ch = run.channel
        data = run.rundata
        fname = "{results_dir}{type}{bd}{ch}_{samp:%2d}_{sig%2d}.png"

        #Plot the data snapshot
        adc.plot_snap(data, fname.format(results_dir, "snap", bd, ch, samp, sig))

        #Data average
        ave = np.average(data)
        rms, loading_factor = adc.get_rms_loading_factor(data)

        #Get the histogram data, append to histdata collection
        hist.append(bd+ch)
        hist.append(sig)
        hist.append("{%0.2f}"%ave)
        for calc in np.histogram(data, bins=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16])[0]:
            hist.append(calc)
        histdata.append(hist)

        #Calculate PSD, SFDR, ENOB, SINAD, append to results collection
        psd_filename = fname.format(results_dir, "psd", bd, ch, samp, sig)
        adc.gen_psd(run.rundata, float(run.samplingfreq), nfft = 8192, plotdB=True, filename = psd_filename)
        sample.append(run.board)
        sample.append(run.channel)
        sample.append(run.samplingfreq)
        for calc in adc.get_sfdr_sinad_from_psd(run.signalfreq, fname = 'psd'):
            sample.append(calc)
        sample.append("{%0.2f}"%ave)
        sample.append("{%0.2f}"%rms)
        sample.append("{%0.2f}"%loading_factor)
        results.append(sample)

    #Pretty print the histogram into table
    headers = ['board', 'sig_freq', 'average', '0', '1', '2', '3', '4', '5', '6', '7','8','9', '10', '11', '12', '13', '14', '15']
    adc.print_table(args.directory+'results/histogram.txt', date, histdata, headers)

    #Pretty print the results into table
    headers = ['board','channel','samp_freq', 'sig_freq', 'sig_db', 'sfdr', 'sinad', 'enob', 'peak_freq', 'spur_freq', 'average', 'rms', 'loading_factor']
    adc.print_table(args.directory+'results/analysis.txt', date, results, headers)

    #Pretty print the results into plots
    results_filename = args.directory+"results/"+"results_" + str(int(samplingfreq)) + ".png"
    adc.plot_all(results, results_filename)


#This converts csv files that have already been run into raw data and a list of meta-data from the file name

def convert_files(file_location):
    #Each file contains a snapshot of data for signal and sampling frequency
    #FileName example: ADC052020_B3_CD_S15_Txx_DC513_DL410_I0_55.csv
    #files = glob.glob(args.directory+"*.csv")
    allrundata = []
    for csvfile in files:

        #Get data out of filename
        pars = (csvfile.split('/')[-1]).split('_')
        date = pars[0][3:]
        board = pars[1][1]
        channel = pars[2][1]
        samplingfreq = float(pars[3][1:]) * 1000
        signalfreq = float(pars[7][1:])*1000 + float((pars[8].split('.'))[0]) * 10

        #Plots that are for this snap only
        psd_filename = args.directory+"results/"+"psd_" + board + channel + "_" + str(int(samplingfreq)) + "_" + str(int(signalfreq)) + ".png"
        snap_filename = args.directory+"results/"+"snap_" + board + channel + "_" + str(int(samplingfreq)) + "_" + str(int(signalfreq)) + ".png"

        #Create raw data from csv
        data = []
        with open(csvfile) as f:
            for line in f:
                data.append(int(line))
        allrundata.append(c.run(date, board, channel, samplingfreq, signalfreq, data))
    return allrundata



def plot_snap(snap, fname, fromsamp=None, tosamp=None):
   plt.clf() 
   if (fromsamp and tosamp):
       plt.plot(range(fromsamp,tosamp),snap[fromsamp:tosamp])
   else:
       plt.plot(list(range(len(snap))),snap)
   plt.xlabel("Sample")
   plt.ylabel("Amplitude")
   plt.savefig(fname)
   plt.clf() 


def print_table(fname, date, data, headers):
    data.sort()
    outfd = open(fname, 'w')
    outfd.write("Data run on " + date + "\n")
    table = columnar(data,headers)
    outfd.write(table)
    outfd.close()


def get_rms_loading_factor(snap):
  """
  From a snapshot, computes the RMS and loading factor. This helps determine
  the best input power for noise/power ratio.
  """
  rms = np.std(snap)
  loadingFactor = -20.0*math.log10(PEAK/rms)
  print ("RMS = %f, loading factor = %f" % (rms,loadingFactor))
  return rms, loadingFactor

def gen_psd(snap, sample_freq, nfft = None, plotdB=True, filename="psd.png"):
  """
  Takes a snapshot, then computes, plots and writes out the Power Spectral
  Density functions.  The psd function is written into a file named "psd".
  This file will be overwritten with each call.  Arguments:

  nfft The number of points in the psd function.  Defaults to the number of
       points in a snapshot, the maximum which should be used.

  plotdB controls whether the plot is linear in power or in dB
  """
  plt.clf()
  if nfft == None:
    nfft = c.NUM_SAMPLES

  power, freqs = psd(snap, nfft, Fs=sample_freq*1e6, scale_by_freq=True)
  #freqs, power = signal.welch(snap, fs=sample_freq*1e6, nfft=c.NUM_SAMPLES,scaling='density')
  print(len(freqs))
  print(len(power))

  if plotdB:
      plt.step(freqs[2:], 10*np.log10(power)[2:])
  else:
      plt.step(freqs[2:], power[2:])
  plt.grid()
  plt.ylabel('dB/Hz')
  plt.xlabel('Hz')
  plt.title('Power Spectral density')
  plt.savefig(filename)
  #plt.clf()

  data = np.column_stack((freqs/1e6, 10*np.log10(power)))
  np.savetxt("psd", data, fmt=('%7.2f', '%6.1f'))

  return power, freqs

def get_thd(carrier_freq, snap, sample_freq, nfft = None, plotdB=True, filename="psd.png"):
  """
  Takes a snapshot, then computes, plots and writes out the Power Spectral
  Density functions.  The psd function is written into a file named "psd".
  This file will be overwritten with each call.  Arguments:

  nfft The number of points in the psd function.  Defaults to the number of
       points in a snapshot, the maximum which should be used.

  plotdB controls whether the plot is linear in power or in dB
  """
  plt.clf()
  if nfft == None:
    nfft = c.NUM_SAMPLES

  #Compute the first 5 harmonics including aliased frequencies (if the harmonics fall out of the Nyquist band)

  harmonic1=carrier_freq*2.0
  harmonic2=carrier_freq*3.0
  harmonic3=carrier_freq*4.0
  harmonic4=carrier_freq*5.0
  harmonic5=carrier_freq*6.0
  
  power, freqs = psd(snap, nfft, Fs=sample_freq*1e6, scale_by_freq=True)
  #freqs, power = signal.welch(snap, fs=sample_freq*1e6, nfft=c.NUM_SAMPLES,scaling='density')
  print(len(freqs))
  print(len(power))
    

  harmonic1_freq, harmonic1_power = get_harmonic_power_freq(sample_freq, harmonic1, power, freqs)
  print(harmonic1_freq,10*np.log10(harmonic1_power))
  harmonic2_freq, harmonic2_power = get_harmonic_power_freq(sample_freq, harmonic2, power, freqs)
  print(harmonic2_freq,10*np.log10(harmonic2_power))
  harmonic3_freq, harmonic3_power = get_harmonic_power_freq(sample_freq, harmonic3, power, freqs)
  print(harmonic3_freq,10*np.log10(harmonic3_power))
  harmonic4_freq, harmonic4_power = get_harmonic_power_freq(sample_freq, harmonic4, power, freqs)
  print(harmonic4_freq,10*np.log10(harmonic4_power))
  harmonic5_freq, harmonic5_power = get_harmonic_power_freq(sample_freq, harmonic5, power, freqs)
  print(harmonic5_freq,10*np.log10(harmonic5_power))

  #Power in carrier

  powerval=[]
  ind = (np.abs(freqs/1e6 - carrier_freq)).argmin()
  for i in range(-4, 5):
          powerval.append(power[ind-i])
  powerincarrier=max(powerval)
  print(carrier_freq,10*np.log10(powerincarrier))
    
  #Compute the THD
    
  thd = 10*np.log10(powerincarrier) - 10*np.log10(harmonic1_power + harmonic2_power + harmonic3_power + harmonic4_power + harmonic5_power)
    
  #sorted_index_power=np.argsort(power)
  #sorted_power=power[sorted_index_power]
  #sorted_freqs=freqs[sorted_index_power]
  #n=15
  #rslt = sorted_power[-n : ]
  #rslt_freqs = sorted_freqs[-n : ]
  #print("{} largest value:".format(n), 10*np.log10(rslt))
  #print("{} largest value:".format(n), rslt_freqs/1e9)

  #fft_of_snapshot = fft(snap)
  #plt.plot(20*np.log10(2.0/nfft * np.abs(fft_of_snapshot[0:nfft//2]))[10:])
  #plt.grid()
  #plt.show()

  if plotdB:
    plt.step(freqs[10:], 10*np.log10(power)[10:])
  else:
    plt.step(freqs[10:], power[10:])
  plt.grid()
  plt.ylabel('dB/Hz')
  plt.xlabel('Hz')
  plt.title('Power Spectral density')
  plt.savefig(filename)
  #plt.clf()

  data = np.column_stack((freqs/1e6, 10*np.log10(power)))
  np.savetxt("psd", data, fmt=('%7.2f', '%6.1f'))

  return thd

def get_sinad_enob_sfdr(carrier_freq, snap, sample_freq, nfft = None, plotdB=True, filename="psd.png"):
  """
  Takes a snapshot, then computes, plots and writes out the Power Spectral
  Density functions.  The psd function is written into a file named "psd".
  This file will be overwritten with each call.  Arguments:

  nfft The number of points in the psd function.  Defaults to the number of
       points in a snapshot, the maximum which should be used.

  plotdB controls whether the plot is linear in power or in dB
  """
  plt.clf()
  if nfft == None:
    nfft = c.NUM_SAMPLES

  power, freqs = psd(snap, nfft, Fs=sample_freq*1e6, scale_by_freq=True)
  #freqs, power = signal.welch(snap, fs=sample_freq*1e6, nfft=c.NUM_SAMPLES,scaling='density')
  print(len(freqs))
  print(len(power))

  #Power in carrier

  powerval=[]
  ind = (np.abs(freqs/1e6 - carrier_freq)).argmin()
  print(ind)
  for i in range(-4, 5):
         powerval.append(power[ind-i])
  powerincarrier=max(powerval)
  print(carrier_freq,10*np.log10(powerincarrier))

  #Sum of power values exclude first 10 channels and 10 channels around the carrier frequency
  sumpower=[]
  indexToexclude=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, ind-4, ind-3, ind-2, ind-1, ind, ind+1, ind+2, ind+3, ind+4]
  newpower=np.delete(power,indexToexclude)
  sumpower=newpower.sum()
  print(10*np.log10(sumpower))
  
  #Sum of power values exclude first 2 channels and 5 channels around the carrier frequency
  indexToexclude=[0, 1,  ind-2, ind-1, ind, ind+1, ind+2]
  newpower=np.delete(power,indexToexclude)
  sfdrpower=max(newpower)
  print((np.argmax(newpower)+7)*2, 10*np.log10(sfdrpower))
  sfdr = 10*np.log10(powerincarrier) - 10*np.log10(sfdrpower)
  
  #Compute the SINAD
  
  sinad = 10*np.log10(powerincarrier) - 10*np.log10(sumpower)
  enob=(sinad-1.76)/6.02
  
  if plotdB:
      plt.step(freqs[10:], 10*np.log10(power)[10:])
  else:
      plt.step(freqs[10:], power[10:])
  plt.grid()
  plt.ylabel('dB/Hz')
  plt.xlabel('Hz')
  plt.title('Power Spectral density')
  plt.savefig(filename)
  #plt.clf()

  data = np.column_stack((freqs/1e6, 10*np.log10(power)))
  np.savetxt("psd", data, fmt=('%7.2f', '%6.1f'))

  return sinad, enob, sfdr

def get_harmonic_power_freq(sampling_frequency, someharmonic, powerarray, freqarray):

    powerval=[]
    if (someharmonic < sampling_frequency/2.0):
        ind = (np.abs(freqarray/1e6 - someharmonic)).argmin() #the argmin method picks the frequency difference closest to zero (smallest value pick), since freqarray-someharmonic == 0 will not work
        for i in range(-4, 5): # Sweep through a small range of frequencies around the computed minimum and pick the spur with the most power
            powerval.append(powerarray[ind-i])
        poweratharmonic=max(powerval)
        ret_frequency=someharmonic
    elif (someharmonic > sampling_frequency/2.0):
        aliased_freq=np.fabs(someharmonic - sampling_frequency*round(someharmonic/sampling_frequency))
        print(aliased_freq)
        ind = (np.abs(freqarray/1e6 - aliased_freq)).argmin()
        for i in range(-4, 5):
            powerval.append(powerarray[ind-i])
        poweratharmonic=max(powerval)
        ret_frequency=aliased_freq
    return ret_frequency, poweratharmonic


def get_sfdr_sinad_from_psd(sig_freq, fname = 'psd'):
  """ 
  Read the psd data from a file and calculate the SFDR and SINAD.  Write the
  results in a file named sfdr_sinad
  """
  
  tot_pwr = 0.0 #Total of signal power
  in_peak = False
  spur_pwr = 0.0
  sig_pwr = 0

  for line in open(fname, 'r'):
    #print(line)
    f, d = line.split()
    freq = float(f)
    db = float(d)
    pwr = 10**(db/10.)

    #Calculate the total power
    tot_pwr += pwr

    #Calculate the signal frequency power
    
    #Check to see if this is the signal freq and assign threshold accordingly
    #I established these thresholds by eyeballing the PSD (FIXME?)
    if abs(freq - sig_freq) < 4: 
        threshold = -70
    else:
        threshold = -90


    if in_peak: #Were we in a peak in the last value?
        if db < threshold: #we've just left the peak -- time to save the values
            in_peak = False
            if abs(peak_freq - sig_freq) <= 1: #Is this the peak at the signal?
                sig_pwr = pwr_in_peak #Save the pwr_in_peak to total signal power
                sig_db = peak_db #This is the peak db (not total)
                sig_freq_meas = peak_freq #This is the measured peak freq
            else: #We're in a harmonic
                if pwr_in_peak > spur_pwr: #Checking to see if this is the highest power spur
                    spur_pwr = pwr_in_peak
                    spur_db = peak_db
                    spur_freq = peak_freq
        else: #we're still in the peak
            pwr_in_peak += pwr #Keep adding up the power
            if db > peak_db: #Is this the highest db in this peak so far?
                peak_db = db
                peak_freq = freq
    elif (db > threshold): #We're about to go into the peak
        pwr_in_peak = pwr #Set all the values to the first in-peak signal
        peak_freq = freq
        peak_db = db
        in_peak = True

  if not(sig_pwr):
      print("ERROR Couldn't find a peak signal near the signal frequency.")
      return[0,0,0,0,0,0,0,0,]
  if not(spur_pwr):
      print("ERROR Couldn't find a spur frequency.")
      return[0,0,0,0,0,0,0,0,]
  
  sfdr = 10.0*np.log10(sig_pwr / spur_pwr)
  sinad = 10.0*np.log10(sig_pwr / (tot_pwr - sig_pwr))
  enob = (sinad - 1.76)/6.02
    
  return [sig_freq, sig_db, f"{sfdr:.2f}", f"{sinad:.2f}", f"{enob:.2f}", sig_freq_meas, 10.0*np.log10(sig_pwr), spur_freq]

def plot_all(results, fname):
    colors = ['b','g','r','c','m','y','k','tomato']
    linetype = [':','--','-.','-',':','--','-.','-']
    sig_freq = []
    sfdr = []
    sinad = []
    enob = []
    samp_freq = float(results[0][2])
    lastchannel = results[0][1]
    lastboard = results[0][0]
    i = 0
    c = 0
    plt.clf()
    fig, axs = plt.subplots(3, 1)
    axs[0].set_ylabel("enob")
    axs[1].set_ylabel("sfdr")
    axs[2].set_ylabel("sinad")
    axs[2].set_xlabel("Signal Frequency")

    for samp in results:
        board = samp[0]
        channel = samp[1]
        if (lastchannel != channel) or (i == (len(results) - 1)):
            axs[0].plot(sig_freq, enob, marker = '.', linestyle = linetype[c], label = lastboard+lastchannel, color = colors[c])
            axs[1].plot(sig_freq, sfdr, marker = '.', linestyle = linetype[c], color = colors[c])
            axs[2].plot(sig_freq, sinad, marker = '.', linestyle = linetype[c], color = colors[c])
            sig_freq = []
            sfdr = []
            sinad = []
            enob = []
            c = c + 1
        sig_freq.append(float(samp[3]))
        sfdr.append(float(samp[5]))
        sinad.append(float(samp[6]))
        enob.append(float(samp[7]))
        lastchannel = channel 
        lastboard = board
        i=i+1
    fig.legend()
    plt.savefig(fname)
    plt.clf()

def get_hist_from_snapshot(data):
   hist = np.bincount(data, minlength=16)
   print(hist)

def plot_histogram(data, fname):
   plt.clf()
   plt.plot(list(range(16)),data)
   plt.xlabel("Bins")
   plt.ylabel("Sample size")
   plt.savefig(fname)
   plt.clf()

def fit_hist(type='sin', fname='hist_cores'):

  #histogram cores file is arranged from 0 to 15
  
  if type == "sin":
    fit_function = cumsin
  else:
    fit_function = cumgaussian
  
  # get the data as a 4x16 array
  hist = np.genfromtxt(fname, dtype=float)
  #sum the data
  t = float(sum(hist))
  #get the percentage for each 
  cumhist=cumsum(hist[core])/t

  args = (codes[0:255], cumhist[0:255], fit_function)
  plsq = leastsq(hist_residuals, [135,0], args)
  extended_fit = empty(258, dtype=float)
  cumresid = hist_residuals(plsq[0],codes, cumhist, fit_function)
  extended_fit[1:257] = cumhist-cumresid
  extended_fit[0] = 2 * extended_fit[1] - extended_fit[2]
  extended_fit[257] = 2 * extended_fit[256] - extended_fit[255]
  # invert the sign of cumresid so inl corrections will be correct
  for i in range(16):
    if(cumresid[i] > 0 and extended_fit[i+2] > extended_fit[i+1]):
      coderesid[i] = -cumresid[i] / (extended_fit[i+2] - extended_fit[i+1])
    elif(extended_fit[i+1] > extended_fit[i]):
      coderesid[i] = -cumresid[i] / (extended_fit[i+1] - extended_fit[i])
    else:
      coderesid[i]=0
  return plsq[0], coderesid

