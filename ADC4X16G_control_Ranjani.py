#ADC16G Control Program
#Must be run under Python 3.xx
#ADC16G_four_channels_v00.py: April 11, 2020, started with v04 of single-channel version
#v01: added channel t bitshift function
#v07 added support for RF generator control
#v08 added OS offset adjust function
#v09 added support for second Nyquist zone ENOB test
#v10 added NPR measurement
#v11 added DACADJ function
########
#New effort for UDP interface

import os
import sys
import socket
import time
import serial
import string
import matplotlib.pyplot as plt
import numpy as np
import math
import adc_test as adc
import constants as c
import pyvisa
from time import gmtime, strftime
import anritsu_sg_funcs as setgen

#Set this to match whatever your OS has assigned the com port to
serial_port = '/dev/ttyUSB1'

#Set to 1 to use ethernet interface, 0 to use serial one
use_udp = 1
#Send to hard-coded VCU128 address
UDP_DEST_IP = "192.168.1.10"
#VCU128 expects commands on this port
UDP_CMD_PORT= 60000

#Make a filename of form ADC052020_B4_CA_S16_T35_DC513_DL410_I7_5.csv
# With date, Board SN, Channel, Sampling freq, Temperature, DAC CRL (DC), DAC LSB (DL), Input freq (in GHz)
date = "053120"
BoardSN = "3"
Channel = "D"
Sample_freq = "16"
Temp = "44"
DAC_CRL = "513"
DAC_LSB = "410"
InputFreq = "99"  #we'll fill this in later
datafile = "./data/ADC" + date + "_B" + BoardSN + "_C" + Channel + "_S" + Sample_freq + "_T" + Temp + "_DC" + DAC_CRL + "_DL" + DAC_LSB 
enob_file = "./data/ENOB.csv"
configfile = "./config.txt"
avg_psd_file = "./avg_psd.csv"
log_file = "./logfile.csv"

#Set this if generator is present- this doesn't work with the UDP interface
RF_gen_present = 0
#To avoid overdriving the inputs:
max_power_to_board = 2
#For the ENOB test, we can level up the amplitude at each test frequency, to take out rolloff, or not
compensate_for_rolloff = 1
#If we use an external attenuator on the input, set the value here, in dB (positive value, else 0)
ext_atten = 6
#We also need to set the initial generator power for the amplitude adjustment
initial_ENOB_generator_power = -8 + ext_atten
#And the target measured amplitude that we want to adjust to for each freq, or at least for the initial freq
target_ENOB_amplitude = -48
#Also the tolerance we wish to hit with the initial adjustment, in dB
ENOB_amp_tolerance = 0.25
#Set the target offset value to be used in the OS command (any reason this should ever not be 7.5?)
target_offset = 7.5
#Set the tolerance for the OS adjustment
offset_adjust_tolerance = 0.05
#Set the gain from offset DAC value to actual offset, empirically determined (same for all channels?)
dac_to_offset_gain = .016
#Save the config.txt DAC values here each time we read them- 9 places, we'll skip 0 and use 1 to 8
initial_DACvals = [-1,-1,-1,-1,-1,-1,-1,-1, -1]

if RF_gen_present:
    #Connect to the Anritsu MG3692C at default static IP 192.168.0.254:
    rm = pyvisa.ResourceManager()
    RF_gen = rm.open_resource("TCPIP::192.168.0.254::inst0::INSTR")
    print(RF_gen.query('*IDN?'))
    RF_gen.write('SYST:LANG "SCPI"')
    #Set to 500MHz, -8dBm
    #RF_gen.write("FREQ:CW " + str(5e8))
    #RF_gen.write("POW " + str(-8 + ext_atten))
    #RF_gen.write("OUTP ON")

#Set this to debug without hardware connected
no_hw = 0

#Set this to set the four ADC DAC outputs ON
DAC_ON = 0

sleep_time = .1
debug_print = 0

sweepfile = "./data/SWEEP_SN_CH_GS.csv"

#The FIFO holds 8k 32b words, so 64k 4b samples.  Set this value to no more than 64k, and a multiple of 8
samples_2_get = 4096
samples_2_get = samples_2_get & 0xffffff8

#A list of 4b values for each ADC: bit3 = DATAON, bit2 = DACON, bit1 = PRBSON, bit0 = CLKSEL
#Initialize to CLK = HS, PRBS ON, DAC ON, DATA OFF, (bits are entered in 0, 1, 2, 3 order)
ADC_params = []
ADC_params.append([0,1,1,0])
ADC_params.append([0,1,1,0])
ADC_params.append([0,1,1,0])
ADC_params.append([0,1,1,0])

def flush_rx_buf():
    dumpcount = 0    
    #How big is the UDP buffer?  This is just guesswork
    while (dumpcount<32):
        try:
            #print (dumpcount)
            dumpbytes = sock.recvfrom(2048)
            dumpcount +=1
        except:
            break    

def ser_slow(text):
    if use_udp:
        byte_list = bytearray(64)
        for n in range(len(text)): byte_list[n] = ord(text[n])
        sendit(byte_list)
        time.sleep(sleep_time)
    else:
        bytes_to_send = text.encode('utf-8')
        ser.write(bytes_to_send)
        if debug_print:print (bytes_to_send)
        time.sleep(sleep_time)


#payload is a bytearray of the desired length
def sendit(payload):
    sock.sendto(bytes(payload), (UDP_DEST_IP, UDP_CMD_PORT))
    time.sleep(.1)
    if debug_print: print (payload)


#This function writes those lists out to the ADC control reg
def setADC():
    if DAC_ON == 1:
        adc_a = 8*ADC_params[0][3] + 4 + 2*ADC_params[0][1] + ADC_params[0][0]
        adc_b = 8*ADC_params[1][3] + 4 + 2*ADC_params[1][1] + ADC_params[1][0]
        adc_c = 8*ADC_params[2][3] + 4 + 2*ADC_params[2][1] + ADC_params[2][0]
        adc_d = 8*ADC_params[3][3] + 4 + 2*ADC_params[3][1] + ADC_params[3][0]
    else:
        adc_a = 8*ADC_params[0][3] + 2*ADC_params[0][1] + ADC_params[0][0]
        adc_b = 8*ADC_params[1][3] + 2*ADC_params[1][1] + ADC_params[1][0]
        adc_c = 8*ADC_params[2][3] + 2*ADC_params[2][1] + ADC_params[2][0]
        adc_d = 8*ADC_params[3][3] + 2*ADC_params[3][1] + ADC_params[3][0]
    
    string_to_send = hex((adc_d<<12) + (adc_c<<8) + (adc_b<<4) + adc_a) + "X"
    string_to_send = "0000" + string_to_send.split('x')[1]
    #print(string_to_send)
    if (no_hw == 0):ser_slow(string_to_send)
    return string_to_send
    
   
def get_samples(chan, nsamp, val_list):
    #Send the "Take Data" command
    ser_slow(str(chan) + 'T')
    if use_udp:
        time.sleep(.1)
        #Hardware always delivers 4 packets of 1kB each, 8k samples (2 per byte)
        #We'll store all 8k here
        full_list = []
        for packet in range(4):
            reply = sock.recvfrom(1024)
            bytesback = reply[0]
            #print(len(bytesback))
            for n in range(1024):
                full_list.append((bytesback[n]) & 0xf)
                full_list.append(bytesback[n] >>4)
        #But to match UART code, we deliver only a multiple of 256 from this routine
        nsamp = int(nsamp/256) * 256
        for n in range (nsamp): val_list.append(full_list[n])
    else:
        #dump old data
        while ser.in_waiting > 0:
            bytes= ser.read(1)
        #Send the "Take Data" command
        #break the data acquisition into blocks of 256 samples, to not fill the PC buffer
        nsamp = int(nsamp/256) * 256
        numloops = int(nsamp/256)
        for loop in range(numloops):
            while ser.in_waiting < 128:  #wait til 256 samples, two samples per byte
                #print(ser.in_waiting)
                a = 2
            bytes= ser.read(128)
            #print (bytes)
            for n in range(128):
                #print(hex(bytes[n]))
                val_list.append((bytes[n] & 0xf))
                val_list.append((bytes[n]>>4) & 0xf)
        #wait for the rest of the data to come out
        time.sleep(0.6)
            
def bit_shift(adc_chan, bit, steps):
        #numsteps needs to be in hex
        if steps == 0: return
        numsteps = hex(steps)
        vals=[]
        #bit is hex, 0 to 3      
        vals.append(str(adc_chan))
        vals.append(str(bit))
        vals.append(numsteps.split('x')[1])
        string_to_send = ""
        for n in range(3):
            string_to_send += vals[n].rjust(4,'0')        
        string_to_send += 'P'
        #print(string_to_send)
        ser_slow(string_to_send)

def rms(inlist):
    mean = sum(inlist)/len(inlist)
    result = 0
    for val in inlist:
        result += (val - mean)**2
    return (result/len(inlist)) ** 0.5

def check_alignment(adc_chan):
        #Returns a 0 if alignment is good, 1 if bad
        samples_2_get = 1024
        #CLKSEL = 0, PRBS ON, DAC ON, DATA OFF all channels
        for i in range(4): ADC_params[i] = [0,1,1,0]
        setADC()
        #XOR OFF
        ser_slow('0Z')                
        #pattern_match ON
        ser_slow('1Y')      
        val_list = []
        get_samples(adc_chan, samples_2_get, val_list)     
        bit3=[]
        bit2=[]
        bit1=[]
        bit0=[]
        for val in val_list:
            bit3.append((val & 0x8) == 0x8)
            bit2.append((val & 0x4) == 0x4)
            bit1.append((val & 0x2) == 0x2) 
            bit0.append((val & 0x1) == 0x1)
        #save the 32b patterns in a file
        pat_array0 = []
        pat_array1 = []
        pat_array2 = []
        pat_array3 = []
        #get the 32-bit pattern at offset 200 for bit3
        numbits = 32
        match_pattern = 0
        test_offset = 200
        for n in range(test_offset, test_offset + numbits):
            match_pattern = (match_pattern<<1) | bit3[n]
        print("Match pattern = " + hex(match_pattern))
        #now find the position of that pattern in each of the bits
        #We'll record those positions here
        match_pos = [999,999,999,999]
        for position in range(0, samples_2_get - numbits):
            pattern = 0
            for n in range(0,numbits):
                pattern = (pattern<<1) | bit3[position + n]
            pat_array3.append(pattern)
            if (pattern == match_pattern): 
                match_pos[3] = position
        for position in range(0, samples_2_get - numbits):
            pattern = 0
            for n in range(0,numbits):
                pattern = (pattern<<1) | bit2[position + n]
            pat_array2.append(pattern)
            if (pattern == match_pattern): 
                match_pos[2] = position
        for position in range(0, samples_2_get - numbits):
            pattern = 0
            for n in range(0,numbits):
                pattern = (pattern<<1) | bit1[position + n]
            pat_array1.append(pattern)
            if (pattern == match_pattern): 
                match_pos[1] = position
        for position in range(0, samples_2_get - numbits):
            pattern = 0
            for n in range(0,numbits):
                pattern = (pattern<<1) | bit0[position + n]
            pat_array0.append(pattern)
            if (pattern == match_pattern): 
                match_pos[0] = position
        print("Check Alignment", end = "")
        print(match_pos)
        fhand1 = open("./patfile.csv", 'w')
        for n in range(0, samples_2_get - numbits):
            fhand1.write(hex(pat_array3[n]) + ',' + hex(pat_array2[n]) + ',' + hex(pat_array1[n]) + ',' + hex(pat_array0[n]) + '\n')
        fhand1.close()
        time.sleep(.5)
        if (match_pos[0] == match_pos[1]) & (match_pos[1] == match_pos[2]) & (match_pos[2] == match_pos[3]):
            return 0
        else: return 1

def align_all():
        for trial in range(1,5):
            print("")
            print("Trial #", trial)
            #Reset the transceivers and logic
            ser_slow('R')
            time.sleep(1)
            #Reset the data fifos
            ser_slow('V')
            #set up the hardware.
            #CLKSEL = 0, PRBS ON, DAC ON, DATA OFF all channels
            for i in range(4): ADC_params[i] = [0,1,1,0]
            setADC()
            #XOR OFF
            ser_slow('0Z')                
            #pattern_match ON
            ser_slow('1Y')      
            samples_2_get = 1024
            align_fail = [0,0,0,0]
            #We'll do the two crossed-over channels first, and do a check_alignment
            chan_list = [1, 2, 0, 3]
            for adc_chan in chan_list:
                #Reset the data fifos
                #ser_slow('V')
                print("adjusting ADC channel ", adc_chan)
                val_list = []
                get_samples(adc_chan, samples_2_get, val_list)
                bit3=[]
                bit2=[]
                bit1=[]
                bit0=[]
                for val in val_list:
                    bit3.append((val & 0x8) == 0x8)
                    bit2.append((val & 0x4) == 0x4)
                    bit1.append((val & 0x2) == 0x2) 
                    bit0.append((val & 0x1) == 0x1)
                #get the 32-bit pattern at some offset for bit3
                numbits = 32
                match_pattern = 0
                test_offset = 200
                for n in range(test_offset, test_offset + numbits):
                    match_pattern = (match_pattern<<1) | bit3[n]
                print("Match pattern = " + hex(match_pattern))
                #now find the position of that pattern in each of the bits
                #We'll record those positions here
                match_pos = [999,999,999,999]
                for position in range(test_offset -64, samples_2_get - numbits):
                    pattern = 0
                    for n in range(0,numbits):
                        pattern = (pattern<<1) | bit3[position + n]
                    if (pattern == match_pattern): 
                        match_pos[3] = position
                for position in range(test_offset -64, samples_2_get - numbits):
                    pattern = 0
                    for n in range(0,numbits):
                        pattern = (pattern<<1) | bit2[position + n]
                    if (pattern == match_pattern): 
                        match_pos[2] = position
                for position in range(test_offset-64, samples_2_get - numbits):
                    pattern = 0
                    for n in range(0,numbits):
                        pattern = (pattern<<1) | bit1[position + n]
                    if (pattern == match_pattern): 
                        match_pos[1] = position
                for position in range(test_offset-64, samples_2_get - numbits):
                    pattern = 0
                    for n in range(0,numbits):
                        pattern = (pattern<<1) | bit0[position + n]
                    if (pattern == match_pattern): 
                        match_pos[0] = position
                print("Offset of each lane's match pattern ", match_pos)
                #Now we calculate how many bits to shift each channel to align them
                min_pos = min(match_pos)
                max_pos = max(match_pos)
                min_chan = match_pos.index(min(match_pos))
                max_chan = match_pos.index(max(match_pos))
                if min_pos == 999: 
                    print("No pattern match in channel " + str(min_chan))
                    print("Alignment failed for channel ", adc_chan)
                    align_fail[adc_chan] = 1
                    time.sleep(0.5)
                for n in range(3, -1, -1):
                    steps_to_shift = match_pos[n] - min_pos
                    if steps_to_shift > 63: 
                        print("Necessary shift exceeds 63 in bit ", n)
                        print("Alignment failed for channel ", adc_chan)
                        align_fail[adc_chan] = 1
                        time.sleep(0.5)
                            
                #do the adjustment
                if align_fail[adc_chan] == 0:
                    for n in range(3, -1, -1):
                        if (match_pos[n] != 999):
                            steps_to_shift = match_pos[n] - min_pos
                            if steps_to_shift > 64: steps_to_shift = 64
                            print("Shift bit " + str(n) + " " + str(steps_to_shift))                   
                            bit_shift(adc_chan, n, steps_to_shift)
                            time.sleep(.1)
                else:break
            #For channels 1 and 2 check the alignment
            if align_fail == [0,0,0,0]:
                for adc_chan in range(4):
                    print("Checking alignment channel ", adc_chan)
                    align_fail[adc_chan] = check_alignment(adc_chan)
                    if align_fail[adc_chan] == 1: break
            if align_fail == [0,0,0,0]:
                print("Alignment successful")
                print("")
                break
            else: 
                print("Alignment Failed")
                print("")
        #pattern_match On
        ser_slow('1Y')  
        #pattern_match OFF
        ser_slow('0Y')  
        #Now set up the system for real data
        #CLKSEL = 0, PRBS ON, DAC ON, DATA ON all channels
        for i in range(4): ADC_params[i] = [0,1,1,1]
        setADC()
        #XOR ON
        ser_slow("1Z")
        return trial

def set_freq(freq):
    RF_gen.write("FREQ:CW " +str(freq*1000000))
    #inp = input("Set freq to " + str(freq))
    return
    
def set_level(power):
    #don't drive the board too hard!
    if power > max_power_to_board + ext_atten: power = max_power_to_board + ext_atten
    RF_gen.write("POW " +str(power))
    if power == max_power_to_board + ext_atten: return 1
    else: return 0
#Adjust the amplitude to get close to a certain target amplitude, for use in the ENOB test        
def adjust_amplitude(adc_channel):
    print("Adjusting RF Power")
    #This is the level we initially set the RF generator to, in dBm.  Should be in the linear range of the ADC
    rf_power = initial_ENOB_generator_power
    samples_2_get = 8192
    output_power = -999
    while abs(output_power - target_ENOB_amplitude) > ENOB_amp_tolerance:
        retval = set_level(rf_power)
        if retval == 1: return rf_power
        #inp = input("****")
        time.sleep(0.2)
        val_list = []
        get_samples(adc_chan, samples_2_get, val_list)
        adc.gen_psd(val_list,fsample,samples_2_get, True, "./psd.pdf")
        if freq < fsample/2: aliased_freq = freq
        else: aliased_freq = fsample - freq
        results = adc.get_sfdr_sinad_from_psd(aliased_freq)
        print("RF level = ", rf_power, end = '')
        print("  average value = ", sum(val_list)/len(val_list), end = '')
        print("  rms = ", rms(val_list))
        print("Peak at " + str(results[5]) + " MHz Power = " + str(results[6]) + " dB")
        output_power = results[6]
        rf_power += target_ENOB_amplitude - output_power
    return rf_power
def write_DAC_value(DAC_add, DAC_val):
    print("DAC",DAC_add, "set to ", DAC_val)
    value_hex_no_0x = hex(DAC_val).split('x')[1]
    string_to_send = ""
    string_to_send += str(DAC_add).rjust(4, '0')        
    string_to_send += value_hex_no_0x.rjust(4, '0')        
    string_to_send += 'X'
    #print(string_to_send)
    ser_slow(string_to_send)
    
def set_DACs():
    fhand = open(configfile)
    for line in fhand:
        if line.startswith("*"): continue
        #strip off the comment
        strippedline = line.split('*')[0]
        #Split the tag field from the cs value field
        fields = strippedline.split("=")
        if len(fields) !=2: continue
        tag = fields[0]
        value = int(fields[1])
        if tag.startswith("DAC"):
            vals = tag.split('C')
            reg_add = int(vals[1])
            initial_DACvals[reg_add] = value
            write_DAC_value(reg_add, value)
            
    print (initial_DACvals)
    fhand.close()
    
##########################################################    
##########################################################    
##########################################################    


print (" **********ADC16G Control***************")
if no_hw == 0:
    #clear the ARP table so we sennd an ARP request always
    #This requires administrator privileges, so leave it out for normal operation
    #os.system('arp -d')
    if use_udp == 1:
        try :
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP
            sock.bind(("", UDP_CMD_PORT))
            print ("Socket Created")
        except socket.error as msg :
            print ('Failed to create socket. Error Code : ' + str(msg[0]) + ' Message ' + msg[1])
            sys.exit()    
        sock.settimeout(0.5)
    else:
        try:
            ser = serial.Serial(serial_port, 115200)
        except:
            print ("Check Serial Port Connection")
            quit()
        print("Serial port used: " + ser.name)         # check which port was really used
        
#set DACS to initial values in config.txt
set_DACs()

while True:
    inp = input('''Enter 
    "WR" to write a single register,
    "DACS" to write all the DACs with values from the config.txt file,
    "OS" to adjust the offset DAC values,
    "X1" to turn on, "X0 to turn off, XOR,
    "M1" to turn on, "M0" to turn off, patternmatch,
    "R" to reset transceivers,
    "TP0" or "TP1" to select which set of prbs errors to send to testpoints (0 = A/B, 1 = C/D),
    "P" to bit-slip one bit,
    "AL" to align one channel,
    "ALIGN" to reset and align all channels,
    "E" to report the PRBS error counters,
    "ET" to record PRBS errors and temperature,
    "T to take data and plot it,
    "C" to take data and check alignment,
    "H" to report temperatures,
    "DACADJ" to adjust the gain and offset DACs for a given channel,
    "SW" to do a freq sweep,
    "GO" to do a long-term alignment check,
    "ENOB" to do a series of ENOB tests,
    "PSD" to take data and display the power spectral density,
    "NPR" to take an average of a bunch of spectra, and store in avg_psd.csv
    "THD" to get the total harmonic distortion
    "S_E_S_T" to get SINAD and ENOB and SFDR and THD
    "FREQ_RESP" to get frequency response in 200 MHz increments with 200 MHz at FS
    "MULT_T" to get multiple ADC snapshots
    or "q" to quit\n''')
    if inp == 'q':
        if (use_udp == 0):ser.close()
        if (RF_gen_present):rm.close()
        quit()
    elif (inp == 'WR') | (inp == ''):
        inp = input('''Enter a comma-separated pair:
        REG, and VAL, in 0x-style hex or decimal,
        reg1-8 are DACs, reg0 is ADC Control:
          4 bits each ADC, : bit3 = DATAON, bit2 = DACON, bit1 = PRBSON, bit0 = CLKSEL\n''')
        vals = inp.split(',')
        if len(vals) != 2: 
            print ("Need two values")
            break
        #Allow input in 0x-style hex, or decimal
        reg_add = int(vals[0],0)
        value = int(vals[1],0)
        reg_add_hex_no_0x = hex(reg_add).split('x')[1]
        value_hex_no_0x = hex(value).split('x')[1]
        
        string_to_send = ""
        string_to_send += reg_add_hex_no_0x.rjust(4, '0')        
        string_to_send += value_hex_no_0x.rjust(4, '0')        
        string_to_send += 'X'
        #print(string_to_send)
        ser_slow(string_to_send)
    elif inp == "DACS":
        set_DACs()
        
    elif inp == "M0": ser_slow('0Y')
    elif inp == "M1": ser_slow('1Y')  
    elif inp == "X0": ser_slow('0Z')
    elif inp == "X1": ser_slow('1Z')  
    elif inp == "TP0": ser_slow('0S')
    elif inp == "TP1": ser_slow('1S')  

    elif inp == 'R':
        ser_slow('R')
    elif inp == 'H':
        if (use_udp == 0):ser.reset_input_buffer()  #dump old data
        ser_slow('H')
        if use_udp:
            time.sleep(.1)
            reply = sock.recvfrom(1024)
            bytesback = reply[0]
            temp0 = (int((bytesback[1])<<8) + int(bytesback[0]))/4
            temp1 = (int((bytesback[3])<<8) + int(bytesback[2]))/4
            
        else:
            while ser.in_waiting < 4:  #wait for 4 bytes
                #print(ser.in_waiting)
                a = 2
            bytes= ser.read(4)
            #for n in range(4):print(int(bytes[n]))
            temp0 = (int((bytes[1])<<8) + int(bytes[0]))/4
            temp1 = (int((bytes[3])<<8) + int(bytes[2]))/4
        print("U32 temp = " +str(temp0) + " U33 temp = " + str(temp1))
        time.sleep(1)
    elif (inp == 'P'):
        #inp1 = input("Which ADC CHannel (0-3)?")
        #adc_chan = int(inp1)
        #val_list = []
        #get_samples(adc_chan, 256, val_list)
        inp = input('''Enter a comma-separated triple:
        ADC(0-3), BIT(0-3) and NUMSLIPS(0-63), decimal\n''')
        vals = inp.split(',')
        bit_shift(int(vals[0]), int(vals[1]), int(vals[2]))

    elif (inp == 'PC'):
        #inp1 = input("Which ADC CHannel (0-3)?")
        #adc_chan = int(inp1)
        #val_list = []
        #get_samples(adc_chan, 256, val_list)
        vals = [0]*3
        for nbits in range(1,10):
          for which_adc in range(0,4):
            for which_bit in range(0,4):
                vals[0]=which_adc
                vals[1]=which_bit
                vals[2]=nbits
                print(vals)
                bit_shift(int(vals[0]), int(vals[1]), int(vals[2]))
                time.sleep(1)
                align_all()
                time.sleep(1)

    elif (inp == 'ALIGN'): 
        align_all()
        
        #Now take and display all four channels
        val_list0=[]
        val_list1=[]
        val_list2=[]
        val_list3=[]      
        get_samples(0, 1024, val_list0)   
        #time.sleep(.5)
        get_samples(1, 1024, val_list1)
        #time.sleep(.5)
        get_samples(2, 1024, val_list2)
        #time.sleep(.5)
        get_samples(3, 1024, val_list3)
        
        #A 600-by-600 pixel plot
        plt.figure(figsize = (6,6))
        t = np.arange(len(val_list0))
        ax = plt.subplot(221)
        ax.set(ylim=(0, 15))
        ax.set_yticks([0, 2.5, 5, 7.5, 10, 12.5, 15])
        ax.set_yticklabels([0, 2.5, 5, 7.5, 10, 12.5, 15])
        plt.plot(t, val_list0)
        t = np.arange(len(val_list1))
        ax = plt.subplot(222)
        ax.set(ylim=(0, 15))
        ax.set_yticks([0, 2.5, 5, 7.5, 10, 12.5, 15])
        ax.set_yticklabels([0, 2.5, 5, 7.5, 10, 12.5, 15])
        plt.plot(t, val_list1)
        t = np.arange(len(val_list2))
        ax = plt.subplot(223)
        ax.set(ylim=(0, 15))
        ax.set_yticks([0, 2.5, 5, 7.5, 10, 12.5, 15])
        ax.set_yticklabels([0, 2.5, 5, 7.5, 10, 12.5, 15])
        plt.plot(t, val_list2)
        t = np.arange(len(val_list3))
        ax = plt.subplot(224)
        ax.set(ylim=(0, 15))
        ax.set_yticks([0, 2.5, 5, 7.5, 10, 12.5, 15])
        ax.set_yticklabels([0, 2.5, 5, 7.5, 10, 12.5, 15])
        plt.plot(t, val_list3)

        plt.show()
        #plt.clf()
    elif (inp == 'T') | (inp == 'C') | (inp == "AL"):
        inp2 = ""
        inp1 = input("Which ADC CHannel (0-3, ALL for all 4)?")
        if inp1 == "ALL":
            val_list0=[]
            val_list1=[]
            val_list2=[]
            val_list3=[]      
            get_samples(0, 1024, val_list0)   
            #time.sleep(.5)
            get_samples(1, 1024, val_list1)
            #time.sleep(.5)
            get_samples(2, 1024, val_list2)
            #time.sleep(.5)
            get_samples(3, 1024, val_list3)
            
            #A 600-by-600 pixel plot
            textstr = 'Mean=%.2f\nRMS=%.2f\n'%(sum(val_list0)/len(val_list0), rms(val_list0))
            plt.figure(figsize = (6,6))
            t = np.arange(len(val_list0))
            ax = plt.subplot(221)
            ax.set(ylim=(0, 15))
            ax.set_yticks([0, 2.5, 5, 7.5, 10, 12.5, 15])
            ax.set_yticklabels([0, 2.5, 5, 7.5, 10, 12.5, 15])
            plt.plot(t, val_list0)
            plt.text(0.02, 0.9, textstr, fontsize=10, transform=plt.gcf().transFigure )
            t = np.arange(len(val_list1))
            textstr = 'Mean=%.2f\nRMS=%.2f\n'%(sum(val_list1)/len(val_list1), rms(val_list1))
            ax = plt.subplot(222)
            ax.set(ylim=(0, 15))
            ax.set_yticks([0, 2.5, 5, 7.5, 10, 12.5, 15])
            ax.set_yticklabels([0, 2.5, 5, 7.5, 10, 12.5, 15])
            plt.plot(t, val_list1)
            plt.text(0.32, 0.9, textstr, fontsize=10, transform=plt.gcf().transFigure )
            textstr = 'Mean=%.2f\nRMS=%.2f\n'%(sum(val_list2)/len(val_list2), rms(val_list2))
            t = np.arange(len(val_list2))
            ax = plt.subplot(223)
            ax.set(ylim=(0, 15))
            ax.set_yticks([0, 2.5, 5, 7.5, 10, 12.5, 15])
            ax.set_yticklabels([0, 2.5, 5, 7.5, 10, 12.5, 15])
            plt.plot(t, val_list2)
            plt.text(0.62, 0.9, textstr, fontsize=10, transform=plt.gcf().transFigure )
            t = np.arange(len(val_list3))
            textstr = 'Mean=%.2f\nRMS=%.2f\n'%(sum(val_list3)/len(val_list3), rms(val_list3))
            ax = plt.subplot(224)
            ax.set(ylim=(0, 15))
            ax.set_yticks([0, 2.5, 5, 7.5, 10, 12.5, 15])
            ax.set_yticklabels([0, 2.5, 5, 7.5, 10, 12.5, 15])
            plt.plot(t, val_list3)
            plt.text(0.82, 0.9, textstr, fontsize=10, transform=plt.gcf().transFigure )

            plt.show()
            #plt.clf()
            
        else:
            if inp1 == "": inp1 = "0"
            adc_chan = int(inp1)
            #set up the hardware.  If T, use the existing settings, so we can look at PRBS data if we want
            if (inp == 'AL') | (inp == 'C'):
                samples_2_get = 1024
                #CLKSEL = 0, PRBS ON, DAC ON, DATA OFF all channels
                for i in range(4): ADC_params[i] = [0,1,1,0]
                setADC()
                #XOR OFF
                ser_slow('0Z')                
                #pattern_match ON
                ser_slow('1Y')      
            val_list = []
            if (inp == 'T'):
                inp1 = input("How many multiples of 256 samples (up to 32), default 32?")
                if inp1=="": inp1 = "32"
                samples_2_get = 256 * int(inp1)
                if samples_2_get > 8192: samples_2_get = 8192
                inp2 = input("Input Freq, GHz, format 1_0 \n")
            get_samples(adc_chan, samples_2_get, val_list)
            #print(val_list)
            fhand = open(datafile + "_I" +  inp2 + ".csv", 'w')  
            
            bit3=[]
            bit2=[]
            bit1=[]
            bit0=[]
            for val in val_list:
                #To write out the bits separately:
                #fhand.write(str(val) + ',' + str(val & 0x8)+ ',' + str(val & 0x4)+ ',' + str(val & 0x2)+ ',' + str(val & 0x1) + '\n')
                fhand.write(str(val) +  '\n')
                bit3.append((val & 0x8) == 0x8)
                bit2.append((val & 0x4) == 0x4)
                bit1.append((val & 0x2) == 0x2) 
                bit0.append((val & 0x1) == 0x1)
            fhand.close()
            
            if inp != 'T':
                #save the 32b patterns in a file
                pat_array0 = []
                pat_array1 = []
                pat_array2 = []
                pat_array3 = []
                #get the 32-bit pattern at offset 100 for bit3
                numbits = 32
                match_pattern = 0
                test_offset = 200
                for n in range(test_offset, test_offset + numbits):
                    match_pattern = (match_pattern<<1) | bit3[n]
                print("Match pattern = " + hex(match_pattern))
                #now find the position of that pattern in each of the bits
                #We'll record those positions here
                match_pos = [999,999,999,999]
                for position in range(0, samples_2_get - numbits):
                    pattern = 0
                    for n in range(0,numbits):
                        pattern = (pattern<<1) | bit3[position + n]
                    pat_array3.append(pattern)
                    if (pattern == match_pattern): 
                        match_pos[3] = position
                        #break
                for position in range(0, samples_2_get - numbits):
                    pattern = 0
                    for n in range(0,numbits):
                        pattern = (pattern<<1) | bit2[position + n]
                    pat_array2.append(pattern)
                    if (pattern == match_pattern): 
                        match_pos[2] = position
                        #break
                for position in range(0, samples_2_get - numbits):
                    pattern = 0
                    for n in range(0,numbits):
                        pattern = (pattern<<1) | bit1[position + n]
                    pat_array1.append(pattern)
                    if (pattern == match_pattern): 
                        match_pos[1] = position
                        #break
                for position in range(0, samples_2_get - numbits):
                    pattern = 0
                    for n in range(0,numbits):
                        pattern = (pattern<<1) | bit0[position + n]
                    pat_array0.append(pattern)
                    if (pattern == match_pattern): 
                        match_pos[0] = position
                        #break
                print(match_pos)
                fhand1 = open("./patfile.csv", 'w')
                for n in range(0, samples_2_get - numbits):
                    fhand1.write(hex(pat_array3[n]) + ',' + hex(pat_array2[n]) + ',' + hex(pat_array1[n]) + ',' + hex(pat_array0[n]) + '\n')
                fhand1.close()
            if inp == "T":
                textstr = 'Average Val=%.2f\nRMS=%.2f\n'%(sum(val_list)/len(val_list), rms(val_list))
                t = np.arange(len(val_list))
                y = np.array(val_list)
                plt.figure(1)
                ax = plt.subplot(1,1,1)
                ax.set(ylim=(0, 15))
                ax.set_yticks([0, 2.5, 5, 7.5, 10, 12.5, 15])
                ax.set_yticklabels([0, 2.5, 5, 7.5, 10, 12.5, 15])
                plt.plot(t, val_list)
                plt.text(0.02, 0.9, textstr, fontsize=10, transform=plt.gcf().transFigure )
                plt.show()
                plt.clf()
                print("average value = ", sum(val_list)/len(val_list), end = '')
                print("  rms = ", rms(val_list))
            if inp == "AL":
                min_pos = min(match_pos)
                max_pos = max(match_pos)
                min_chan = match_pos.index(min(match_pos))
                max_chan = match_pos.index(max(match_pos))
                
                #if min_pos == 999: print("No pattern match in channel " + str(min_chan))
                #we'll bump each channel's bit alignment to match the minimum channel
                #for n in range(4):
                for n in range(3, -1, -1):
                    if (match_pos[n] != -1):
                        steps_to_shift = match_pos[n] - min_pos
                        if steps_to_shift > 128: steps_to_shift = 128
                        print("Shift chan " + str(n) + " " + str(steps_to_shift))
                        
                        bit_shift(adc_chan, n, steps_to_shift)
                        time.sleep(.5)
            
            if inp == "C":
                #Now we want to take and display more data, with XOR ON and DATA OFF, which should be all 0s
                #CLKSEL = 0, PRBS ON, DAC ON, DATA OFF all channels
                for i in range(4): ADC_params[i] = [0,1,1,0]
                setADC()
                #XOR ON
                ser_slow("1Z")
                #Turn pattern_match OFF so it doesn't produce a spike every 131us
                ser_slow('0Y')
                time.sleep(.5)
                val_list = []
                get_samples(adc_chan, samples_2_get, val_list)
                fhand = open(datafile, 'w')  
                bit3=[]
                bit2=[]
                bit1=[]
                bit0=[]
                for val in val_list:
                    fhand.write(str(val) + ',' + str(val & 0x8)+ ',' + str(val & 0x4)+ ',' + str(val & 0x2)+ ',' + str(val & 0x1) + '\n')
                    bit3.append((val & 0x8) == 0x8)
                    bit2.append((val & 0x4) == 0x4)
                    bit1.append((val & 0x1) == 0x1)  #note bit-swap here to match lane mapping
                    bit0.append((val & 0x2) == 0x2)
                fhand.close()
                #Turn pattern_match ON so we can cehck testpoints
                ser_slow('1Y')
                t = np.arange(len(val_list))
                y = np.array(val_list)
                plt.figure(1)
                ax = plt.subplot(1,1,1)
                ax.set(ylim=(0, 15))
                ax.set_yticks([0, 2.5, 5, 7.5, 10, 12.5, 15])
                ax.set_yticklabels([0, 2.5, 5, 7.5, 10, 12.5, 15])
                plt.plot(t, val_list)
                plt.show()
                plt.clf()
            if (inp == 'AL') | (inp == 'C'):
                print("Setting for data taking")
                time.sleep(1)
                #Now set up the system for real data
                #CLKSEL = 0, PRBS ON, DAC ON, DATA OFF all channels
                for i in range(4): ADC_params[i] = [0,1,1,1]
                setADC()
                #XOR ON
                ser_slow("1Z")
                #ser_slow('0000001eX')
                #pattern_match OFF
                ser_slow('0Y')      
        
    elif (inp == 'MULT_T'):
        inpfreq=input('Which frequency in MHz or hit enter if all inputs are terminated?   ')
        if (inpfreq == ""):
            inpfreq='NONE'
        for i in range(20):
            val_list0=[]
            val_list1=[]
            val_list2=[]
            val_list3=[]      
            get_samples(0, 1024, val_list0)   
            #time.sleep(.5)
            get_samples(1, 1024, val_list1)
            #time.sleep(.5)
            get_samples(2, 1024, val_list2)
            #time.sleep(.5)
            get_samples(3, 1024, val_list3)
            
            #A 600-by-600 pixel plot
            textstr = 'Mean=%.2f\nRMS=%.2f\n'%(sum(val_list0)/len(val_list0), rms(val_list0))
            fig=plt.figure(figsize = (6,6))
            t = np.arange(len(val_list0))
            ax = plt.subplot(221)
            ax.set(ylim=(0, 15))
            ax.set_yticks([0, 2.5, 5, 7.5, 10, 12.5, 15])
            ax.set_yticklabels([0, 2.5, 5, 7.5, 10, 12.5, 15])
            plt.plot(t, val_list0)
            plt.text(0.02, 0.9, textstr, fontsize=10, transform=plt.gcf().transFigure )
            t = np.arange(len(val_list1))
            textstr = 'Mean=%.2f\nRMS=%.2f\n'%(sum(val_list1)/len(val_list1), rms(val_list1))
            ax = plt.subplot(222)
            ax.set(ylim=(0, 15))
            ax.set_yticks([0, 2.5, 5, 7.5, 10, 12.5, 15])
            ax.set_yticklabels([0, 2.5, 5, 7.5, 10, 12.5, 15])
            plt.plot(t, val_list1)
            plt.text(0.32, 0.9, textstr, fontsize=10, transform=plt.gcf().transFigure )
            textstr = 'Mean=%.2f\nRMS=%.2f\n'%(sum(val_list2)/len(val_list2), rms(val_list2))
            t = np.arange(len(val_list2))
            ax = plt.subplot(223)
            ax.set(ylim=(0, 15))
            ax.set_yticks([0, 2.5, 5, 7.5, 10, 12.5, 15])
            ax.set_yticklabels([0, 2.5, 5, 7.5, 10, 12.5, 15])
            plt.plot(t, val_list2)
            plt.text(0.62, 0.9, textstr, fontsize=10, transform=plt.gcf().transFigure )
            t = np.arange(len(val_list3))
            textstr = 'Mean=%.2f\nRMS=%.2f\n'%(sum(val_list3)/len(val_list3), rms(val_list3))
            ax = plt.subplot(224)
            ax.set(ylim=(0, 15))
            ax.set_yticks([0, 2.5, 5, 7.5, 10, 12.5, 15])
            ax.set_yticklabels([0, 2.5, 5, 7.5, 10, 12.5, 15])
            plt.plot(t, val_list3)
            plt.text(0.82, 0.9, textstr, fontsize=10, transform=plt.gcf().transFigure )
            #plt.show()
            filename='figures/Snapshots_'+ str(inpfreq) + '_' + str(i+19) + '_' +'.png'
            plt.savefig(filename)
            plt.cla()
        plt.close(fig)
        
    if (inp == "E"):
        #CLKSEL = 0, PRBS ON, DAC ON, DATA OFF all channels
        for i in range(4): ADC_params[i] = [0,1,1,0]
        setADC()
        errors = 16 * [0]
        #Tell the MicroBlaze to take data and send it back
        if (use_udp == 0):ser.reset_input_buffer()      #dump old data
        ser_slow('U')
        if use_udp:
            time.sleep(2)
            reply = sock.recvfrom(1024)
            bytesback = reply[0]
            for n in range(16):
                errors[n] = int(bytesback[4*n])
                errors[n] = errors[n] + (int(bytesback[4*n+1])<<8)
                errors[n] = errors[n] + (int(bytesback[4*n+2])<<16)
                errors[n] = errors[n] + (int(bytesback[4*n+3])<<24)           
        else:
            while ser.in_waiting < 64:  #wait for 64 bytes
                #print(ser.in_waiting)
                a = 2
            bytes= ser.read(64)
            for n in range(16):
                errors[n] = int(bytes[4*n])
                errors[n] = errors[n] + (int(bytes[4*n+1])<<8)
                errors[n] = errors[n] + (int(bytes[4*n+2])<<16)
                errors[n] = errors[n] + (int(bytes[4*n+3])<<24)
        for n in range(4):
            err_string = []
            for m in range(4):
                if errors[4*n+m] == 0xffffffff: err_string.append("no_lock")
                else: err_string.append(str(errors[4*n+m]))
            #print("ADC Channel ", n, "\tbit0\t", errors[4*n], "\tbit1\t", errors[4*n+1], "\tbit2\t", errors[4*n+2], "\tbit3\t", errors[4*n+3])       
            print("ADC Channel " + str(n) + "\tbit0\t" + err_string[0] + "\tbit1\t" + err_string[1] + "\tbit2\t" + err_string[2] + "\tbit3\t" + err_string[3])       
       
    if (inp == "ET"):
        inp1 = input("Test interval, seconds?")
        test_int = int(inp1)
        fhand = open(sweepfile, 'w')          
        for trial in range(100):
            if (use_udp == 0):ser.reset_input_buffer()      #dump old data
            ser_slow('H')
            if use_udp:
                time.sleep(.1)
                reply = sock.recvfrom(1024)
                bytesback = reply[0]
                temp0 = (int((bytesback[1])<<8) + int(bytesback[0]))/4
                temp1 = (int((bytesback[3])<<8) + int(bytesback[2]))/4               
            else:
                while ser.in_waiting < 4:  #wait for 4 bytes
                    a = 2
                bytes= ser.read(4)
                temp0 = (int((bytes[1])<<8) + int(bytes[0]))/4
                temp1 = (int((bytes[3])<<8) + int(bytes[2]))/4
        
            #CLKSEL = 0, PRBS ON, DAC ON, DATA OFF all channels
            for i in range(4): ADC_params[i] = [0,1,1,0]
            setADC()
            errors = 16 * [0]
            #Tell the MicroBlaze to take data and send it back
            if (use_udp == 0):ser.reset_input_buffer()      #dump old data
            ser_slow('U')
            if use_udp:
                time.sleep(2)
                reply = sock.recvfrom(1024)
                bytesback = reply[0]
                for n in range(16):
                    errors[n] = int(bytesback[4*n])
                    errors[n] = errors[n] + (int(bytesback[4*n+1])<<8)
                    errors[n] = errors[n] + (int(bytesback[4*n+2])<<16)
                    errors[n] = errors[n] + (int(bytesback[4*n+3])<<24)           
            else:
                while ser.in_waiting < 64:  #wait for 64 bytes
                    #print(ser.in_waiting)
                    a = 2
                bytes= ser.read(64)
                for n in range(16):
                    errors[n] = int(bytes[4*n])
                    errors[n] = errors[n] + (int(bytes[4*n+1])<<8)
                    errors[n] = errors[n] + (int(bytes[4*n+2])<<16)
                    errors[n] = errors[n] + (int(bytes[4*n+3])<<24)
            print("U32 temp = " +str(temp0) + " U33 temp = " + str(temp1))
            
            for n in range(4):
                print("ADC Channel ", n, "\tbit0\t", errors[4*n], "\tbit1\t", errors[4*n+1], "\tbit2\t", errors[4*n+2], "\tbit3\t", errors[4*n+3])       
            print("")
            fhand.write(str(temp0) + ',' + str(temp1)+ ',')
            for n in range(16):
                fhand.write(str(errors[n]) + ',')
            fhand.write('\n')
            time.sleep(test_int)
        fhand.close()
    if (inp == "SW"):
        inp1 = input("channel")
        adc_chan = int(inp1)
        inp1 = input("start_freq, stop_freq, step_freq(GHz), #samples per record (.1, 7.3, .2, 1024)")
        if inp1 == "": inp1 = "0.1, 7.3, .2, 1024"
        vals = inp1.split(",")
        start_freq = float(vals[0])
        stop_freq = float(vals[1])
        step_freq = float(vals[2])
        nsamp = int(vals[3])
        fhand = open(sweepfile, 'w')  
        #for freq in range(start_freq, stop_freq, step_freq):
        freq = start_freq
        while (freq <= stop_freq):
            inp1 = input("Set freq to " + str(freq) + "\n")
            val_list = []
            get_samples(adc_chan, nsamp, val_list)
            vrms = rms(val_list)
            vrms_dB = 20 * math.log(vrms,10)
            fhand.write(str(freq) + ',' + str(vrms)+ ',' + str(vrms_dB)+ '\n')
            print(freq, vrms, vrms_dB)
            freq += step_freq
        fhand.close()
    #else: print("Huh?")        
    if (inp == "GO"):
        inp1 = input("channel")
        if inp1 == "": inp1 = "0"
        adc_chan = int(inp1)
        inp1 = input("RMS Threshold for new alignment")
        if inp1 == "": inp1 = "2.0"
        align_thresh = float(inp1)
        inp1 = input("Sleep interval, seconds")
        if inp1 == "": inp1 = "60"
        sleep_int = int(inp1)
        fhand = open("./align_data.txt", 'w')  
        fhand.write("test#, mean, rms")
        for test in range(0,9999999): 
            print("TEST# " + str(test), end="")
            val_list = []
            get_samples(adc_chan, 8192, val_list)
            print(" channel " + str(adc_chan) + " mean " + str(sum(val_list)/len(val_list)) + " rms " + str(rms(val_list)))
            fhand.write(str(test) + ',' + str(sum(val_list)/len(val_list)) + "," + str(rms(val_list)) + "\n")
            if rms(val_list) > align_thresh : 
                num_trials = align_all()
                fhand.write("*************** ALIGN # trials = " + str(num_trials) + "  *******************\n")
                print("*************** ALIGN # trials = " + str(num_trials) + "  ******************")
            time.sleep(sleep_int)
        fhand.close()
    if (inp == "ENOB"):
        inp1 = input("channel (0)")
        if inp1 == "": adc_chan = 0
        else: adc_chan = int(inp1)
        #inp1 = input("Fstart, Fstop, Fstep, Fsample (550, 8000, 100, 16384) ")
        inp1 = input("Fstart, Fstop, Fstep, Fsample (550, 16000, 200, 16384) ")
        #if inp1 == "": inp1 = "550, 8000, 100, 16384"
        if inp1 == "": inp1 = "550, 16000, 200, 16384"
        vals = inp1.split(",")
        fstart = int(vals[0])
        fstop = int(vals[1])
        fstep = int(vals[2])
        fsample = int(vals[3])
        fhand = open(enob_file, 'w')
        fhand.write("input freq,input power, meas freq, meas power, sfdr, enob\n")
        samples_2_get = 8192
        #CLKSEL = 0, PRBS ON, DAC ON, DATA ON all channels
        for i in range(4): ADC_params[i] = [0,1,1,1]
        setADC()
        #XOR ON
        ser_slow('1Z')                
        #pattern_match OFF
        ser_slow('0Y')      
        show_plots = 0
        for freq in range(fstart, fstop+1, fstep):
            set_freq(freq)
            if (compensate_for_rolloff == 1) | (freq == fstart):
                rf_power = adjust_amplitude(adc_chan)
                print("Amplitude Set")
                #time.sleep(10)
            else: time.sleep(0.2)
            val_list = []
            get_samples(adc_chan, samples_2_get, val_list)
            if show_plots == 1:
                t = np.arange(len(val_list[:128]))
                y = np.array(val_list[:128])
                plt.figure(1)
                plt.plot(t, val_list[:128])
                plt.show()
                plt.clf()
            adc.gen_psd(val_list,fsample,samples_2_get, True, "./psd.pdf")
            if freq < fsample/2: aliased_freq = freq
            else: aliased_freq = fsample - freq
            results = adc.get_sfdr_sinad_from_psd(aliased_freq)
            print (results)
            print("average value = ", sum(val_list)/len(val_list), end = '')
            print("  rms = ", rms(val_list))
            fhand.write(str(freq) + "," + str(rf_power) + "," + str(results[5]) + "," + str(results[6]) + ","+ str(results[2]) + "," + str(results[4]) + "\n")
        fhand.close()    
    if (inp == "PSD"):
        inp1 = input("channel (0)")
        if inp1 == "": adc_chan = 0
        else: adc_chan = int(inp1)
        inp1 = input("sample freq (16384) ")
        if inp1 == "": fsample = 16384
        else: fsample = int(inp1)
        samples_2_get = 8192
        #CLKSEL = 0, PRBS ON, DAC ON, DATA ON all channels
        for i in range(4): ADC_params[i] = [0,1,1,1]
        setADC()
        #XOR ON
        ser_slow('1Z')                
        #pattern_match OFF
        ser_slow('0Y')      
        val_list = []
        get_samples(adc_chan, samples_2_get, val_list)
        results = adc.gen_psd(val_list,fsample,samples_2_get, True, "./psd.pdf")
        powers = list(results[0])
        freqs = list(results[1])
        #print(powers)
        #print(freqs)
        maxpower = (max(powers))
        peak_freq_index = powers.index(maxpower)
        peak_freq = (freqs[peak_freq_index])/1e6
        #print ("Peak Power of " + str(10 * math.log(maxpower,10)) + " dB at " + str(peak_freq) + " Mhz")
        results = adc.get_sfdr_sinad_from_psd(peak_freq)
        #print (results)
        print("average value = ", sum(val_list)/len(val_list), end = '')
        print("  rms = ", rms(val_list))
        print("Peak at " + str(results[5]) + " MHz Power = " + str(results[6]) + " dB")
        print(" ENOB = " + str(results[4]) + " SFDR = " + str(results[2]))
        os.system('psd.pdf')

    if (inp == "THD"):
        inp1 = input("channel (0)")
        if inp1 == "": adc_chan = 0
        else: adc_chan = int(inp1)
        inp1 = input("sample freq (16384) ")
        if inp1 == "": fsample = 16384
        else: fsample = int(inp1)
        #inp1 = input("carrier freq (in MHz) ")
        #if inp1 == "": 
        #    print("You did not enter a valid carrier frequency")
        #    sys.exit()
        #else: carrier_freq = int(inp1)
        samples_2_get = 8192
        timenow=strftime("%Y-%m-%d_%H-%M-%S", gmtime())
        filename='newdata/THD_Ch'+str(adc_chan)+'_'+timenow+'.txt'
        #CLKSEL = 0, PRBS ON, DAC ON, DATA ON all channels
        for i in range(4): ADC_params[i] = [0,1,1,1]
        setADC()
        #XOR ON
        ser_slow('1Z')                
        #pattern_match OFF
        ser_slow('0Y')      
        thd_log = np.zeros(10)
        thd_linear = np.zeros(10)
        frequency = np.zeros(40)
        THD = np.zeros(40)
        instrument=setgen.open_sg()

        #Number of frequencies to compute THD 
        for num_freqs in range(40):
            frequency[num_freqs]=200*(num_freqs+1)
            #Compute power from coarse table
            calc_power=setgen.set_freq(frequency[num_freqs],instrument)
            calc_power=float(calc_power)
            time.sleep(1)
            carrier_freq=frequency[num_freqs]

            #Number of THD measurements to average over
            for nloops in range(10):
               val_list = []
               rms_fs=np.zeros(10)
               rms_fs_mean=4.0  #Some random starting value not within the limits shown below

               while (rms_fs_mean > 5.35 or rms_fs_mean < 5.25):
                 #Number of measurements to obtain mean value of ~ 5.3 (FS loading)
                 for num_times in range(10):
                   get_samples(adc_chan, samples_2_get, val_list)
                   rms_fs[num_times]=rms(val_list)
                 rms_fs_mean=np.mean(rms_fs)
                 if (rms_fs_mean > 5.35):
                     calc_power=calc_power-0.1
                     setgen.set_power(calc_power,instrument)
                 else:
                     calc_power=calc_power+0.1
                     setgen.set_power(calc_power,instrument)
               print('RMS_FS_MEAN IS ',rms_fs_mean)
               thd_log[nloops] = adc.get_thd(carrier_freq, val_list,fsample,samples_2_get, True, "./psd.pdf")
               thd_linear[nloops] = 10**(-thd_log[nloops]/10.0)
            thd_avg=thd_linear.sum()/10
            THD[num_freqs] = 10*np.log10(thd_avg)
            print("THD is  \n", THD[num_freqs])

        data = np.column_stack((frequency, THD))
        np.savetxt(filename, data, fmt=('%7.4f', '%6.2f'))
        setgen.close_sg(instrument)

    if (inp == "FREQ_RESP"):
        inp1 = input("channel (0)")
        if inp1 == "": adc_chan = 0
        else: adc_chan = int(inp1)
        inp1 = input("sample freq (16384) ")
        if inp1 == "": fsample = 16384
        else: fsample = int(inp1)
        #inp1 = input("carrier freq (in MHz) ")
        #if inp1 == "": 
        #    print("You did not enter a valid carrier frequency")
        #    sys.exit()
        #else: carrier_freq = int(inp1)
        samples_2_get = 8192
        timenow=strftime("%Y-%m-%d_%H-%M-%S", gmtime())
        filename='newdata/freq_resp_Ch'+str(adc_chan)+'_'+timenow+'.txt'
        #CLKSEL = 0, PRBS ON, DAC ON, DATA ON all channels
        for i in range(4): ADC_params[i] = [0,1,1,1]
        setADC()
        #XOR ON
        ser_slow('1Z')                
        #pattern_match OFF
        ser_slow('0Y')      
        frequency = np.zeros(80)
        rms_mean=np.zeros(80)
        rms_val=np.zeros(10)
        instrument=setgen.open_sg()

        #Number of frequencies to compute freq response 
        for num_freqs in range(80):
            frequency[num_freqs]=200*(num_freqs+1)
            setgen.set_freq_only(frequency[num_freqs],instrument)
            time.sleep(1)

            #Number of measurements to obtain mean value of rms
            for num_times in range(10):
                   val_list=[]
                   get_samples(adc_chan, samples_2_get, val_list)
                   rms_val[num_times]=rms(val_list)
            rms_mean[num_freqs]=np.mean(rms_val)
            print('RMS_MEAN IS ',rms_mean[num_freqs])

        data = np.column_stack((frequency, rms_mean))
        np.savetxt(filename, data, fmt=('%7.4f', '%6.2f'))
        setgen.close_sg(instrument)

    if (inp == "S_E_S_T"):
        inp1 = input("channel (0)")
        if inp1 == "": adc_chan = 0
        else: adc_chan = int(inp1)
        inp1 = input("sample freq (16384) ")
        if inp1 == "": fsample = 16384
        else: fsample = int(inp1)
        #inp1 = input("carrier freq (in MHz) ")
        #if inp1 == "": 
        #    print("You did not enter a valid carrier frequency")
        #    sys.exit()
        #else: carrier_freq = int(inp1)
        samples_2_get = 8192
        timenow=strftime("%Y-%m-%d_%H-%M-%S", gmtime())
        filename='newdata/SINAD_ENOB_SFDR_THD_Ch'+str(adc_chan)+'_'+timenow+'.txt'
        #CLKSEL = 0, PRBS ON, DAC ON, DATA ON all channels
        for i in range(4): ADC_params[i] = [0,1,1,1]
        setADC()
        #XOR ON
        ser_slow('1Z')                
        #pattern_match OFF
        ser_slow('0Y')      
        frequency = np.zeros(40)
        SINAD = np.zeros(40)
        ENOB = np.zeros(40)
        SFDR = np.zeros(40)
        THD = np.zeros(40)
        thd_log = np.zeros(10)
        thd_linear = np.zeros(10)
        sinad_log = np.zeros(10)
        sinad_linear = np.zeros(10)
        sfdr_log = np.zeros(10)
        sfdr_linear = np.zeros(10)
        enob = np.zeros(10)
        instrument=setgen.open_sg()

        #Number of frequencies to compute SINAD, ENOB, SFDR
        for num_freqs in range(40):
            frequency[num_freqs]=200*(num_freqs+1)
            #Compute power from coarse table
            calc_power=setgen.set_freq(frequency[num_freqs],instrument)
            calc_power=float(calc_power)
            time.sleep(1)
            carrier_freq=frequency[num_freqs]

            num_aver=2
            #Number of measurements to average over
            for nloops in range(num_aver):
               val_list = []
               rms_fs=np.zeros(10)
               rms_fs_mean=4.0  #Some random starting value not within the limits shown below

               while (rms_fs_mean > 5.35 or rms_fs_mean < 5.25):
                 #Number of measurements to obtain mean value of ~ 5.3 (FS loading)
                 for num_times in range(10):
                   get_samples(adc_chan, samples_2_get, val_list)
                   rms_fs[num_times]=rms(val_list)
                 rms_fs_mean=np.mean(rms_fs)
                 if (rms_fs_mean > 5.35):
                     calc_power=calc_power-0.1
                     setgen.set_power(calc_power,instrument)
                 else:
                     calc_power=calc_power+0.1
                     setgen.set_power(calc_power,instrument)
               print('RMS_FS_MEAN IS ',rms_fs_mean)
               sinad_log[nloops], enob[nloops], sfdr_log[nloops] = adc.get_sinad_enob_sfdr(carrier_freq, val_list,fsample,samples_2_get, True, "./psd.pdf")
               sinad_linear[nloops] = 10**(-sinad_log[nloops]/10.0)
               sfdr_linear[nloops] = 10**(-sfdr_log[nloops]/10.0)
               thd_log[nloops] = adc.get_thd(carrier_freq, val_list,fsample,samples_2_get, True, "./psd.pdf")
               thd_linear[nloops] = 10**(-thd_log[nloops]/10.0)
            sinad_avg=sinad_linear.sum()/num_aver
            sfdr_avg=sfdr_linear.sum()/num_aver
            enob_direct=enob.sum()/num_aver
            thd_avg=thd_linear.sum()/num_aver
            THD[num_freqs] = 10*np.log10(thd_avg)
            SINAD[num_freqs] = 10*np.log10(sinad_avg)
            SFDR[num_freqs] = 10*np.log10(sfdr_avg)
            ENOB[num_freqs] = (-SINAD[num_freqs] - 1.76)/6.02
            print("SINAD is  \n", SINAD[num_freqs])
            print("SFDR is  \n", SFDR[num_freqs])
            print("ENOB is  \n", ENOB[num_freqs])
            print("THD is  \n", THD[num_freqs])
            print("enob is  \n", enob_direct)

        data = np.column_stack((frequency, SINAD, SFDR, THD, ENOB))
        np.savetxt(filename, data, fmt=('%7.4f', '%6.2f', '%6.2f', '%6.2f', '%6.3f'))
        setgen.close_sg(instrument)

    if (inp == "OS"):
        if RF_gen_present:
            inp1 = input("Frequency to use, MHz? (550)")
            if inp1 == "": freq = 550
            else: freq = float(inp1)
            set_freq(freq)
            inp1 = input("Level to use, dBm? (0)")
            if inp1 == "": ampl = 0
            else: ampl = float(inp1)
            set_level(ampl)
            time.sleep(0.2)
        inp1= input("which channel (0-3)? (0)")
        if inp1 == "": adc_chan = 0
        else: adc_chan = int(inp1)
        OS_DAC_add = 2*adc_chan + 1
        #We'll store the values that we set here and report them; we start with the config.txt values
        new_OS_DAC_value = initial_DACvals[OS_DAC_add]
        samples_2_get = 8192
        offset = 0
        while abs(np.mean(offset) - target_offset) > offset_adjust_tolerance:
            val_list = []
            offset = np.zeros(50)
            for i in range(50):
               get_samples(adc_chan, samples_2_get, val_list)
               offset[i] = sum(val_list)/len(val_list)
            print(np.mean(offset))
            new_OS_DAC_value = new_OS_DAC_value + int((target_offset - np.mean(offset))/dac_to_offset_gain)
            write_DAC_value(2*adc_chan+1, new_OS_DAC_value)
            time.sleep(0.2)
        print("Adjusted Offset DAC value", new_OS_DAC_value)
                
    if (inp == "NPR"):
        inp1 = input("channel (0)")
        if inp1 == "": adc_chan = 0
        else: adc_chan = int(inp1)
        inp1 = input("Notch center freq, MHz (7025)")
        if inp1 == "": notch_freq = 7025
        else: notch_freq = int(inp1)
        inp1 = input("sample freq (16384) ")
        if inp1 == "": fsample = 16384
        else: fsample = int(inp1)
        samples_2_get = 8192
        psd_length = int(samples_2_get/2 + 1)
        #CLKSEL = 0, PRBS ON, DAC ON, DATA ON all channels
        for i in range(4): ADC_params[i] = [0,1,1,1]
        setADC()
        #XOR ON
        ser_slow('1Z')                
        #pattern_match OFF
        ser_slow('0Y')      
        num_2_average = 40
        power_sum = psd_length * [0.0]
        for rep in range(num_2_average):
            print("run number ", rep)
            val_list = []
            get_samples(adc_chan, samples_2_get, val_list)
            power, freqs = adc.psd(val_list, samples_2_get, Fs=fsample*1e6, detrend=adc.detrend_mean, scale_by_freq=True)
            #report the rms in one run
            if (rep == num_2_average-1):
                ampl = rms(val_list)
            #print(power)
            for f in range(psd_length):
                power_sum[f] += power[f]
        #print(power_sum)
        #We want to average the power inside the notch and compare it to the power 
        # in the adjacent bins
        #For the power in the notch, we'll add up the center bin and 8 bins on each side
        notch_freq_center_bin = int(notch_freq*samples_2_get/fsample)
        p_notch = 0.0
        for bin in range(notch_freq_center_bin-8, notch_freq_center_bin+9):
            p_notch += power_sum[bin]
        p_notch = p_notch/17.0
        p_adjacent = 0.0
        for bin in range(notch_freq_center_bin-50, notch_freq_center_bin-25):
            p_adjacent += power_sum[bin]
        for bin in range(notch_freq_center_bin+25, notch_freq_center_bin+50):
            p_adjacent += power_sum[bin]
        p_adjacent = p_adjacent/50.0
        print("Notch power = ", p_notch, "Adjacent Power = ", p_adjacent)
        print("NPR = ", 10* np.log10(p_adjacent/p_notch), "  Rms = ", ampl, " LSBs")
        fhand = open(avg_psd_file, 'w')
        for f in range(psd_length):
            fhand.write(str(freqs[f]/1e6) + "," + str(10*np.log10(power_sum[f])) + "\n")
        fhand.close()
        
    if (inp == "DACADJ"):
        #Start with the default DAC values stored in config.txt
        set_DACs()
        fhand = open(log_file, 'w')  
        mean_tol_1 = 1.0 #LSBs
        mean_tol_2 = 0.2 #LSBs
        rms_tol = 0.2    #dB
        k1 = .017        #ADCbits/DAC_count
        k2 = -.052       #dB/DAC_count
        max_gain_dac_step = 5
        max_offset_dac_step = 10
        inp = input("Set target mean and rms values (7.5, 2.50)")
        if inp == "": 
            target_mean = 7.5
            target_rms = 2.5
        else: 
            target_mean = float(inp.split(",")[0])
            target_rms = float(inp.split(",")[1])
        inp = input("Which Channel (0)")
        if inp == "": adc_chan = 0
        else: adc_chan = int(inp)
        offset_val=[0]*50
        gain_val=[0]*50
        for i in range(0,50):
            offset_dac_val = initial_DACvals[2 * adc_chan + 1]
            gain_dac_val = initial_DACvals[2 * adc_chan + 2]
            samples_2_get = 8192
            mean = 0.0
            ampl = 0.0
            #We'll adjust the two DACs iteratively.  DAC chan+1 adjust only offset, while DAC chan + 2 affaects both
            #  gain and offset.  But if offset is far off, the ADC output will saturate at 0 or 15, so the computed
            #  gain will be impacted.  We'll limit the size of the gain DAC step so we don't get too far out of whack
            #Get data from the channel being adjusted, check if mean is reasonable
            mean_done = 0
            gain_done = 0
            while ((gain_done & mean_done) == 0):
                print("Coarse adjust offset DAC value for channel ", adc_chan)
                while (1):
                    val_list = []
                    get_samples(adc_chan, samples_2_get, val_list)
                    mean = sum(val_list)/len(val_list)
                    ampl = rms(val_list)
                    print("average value = ", mean, end = '')
                    print("  rms = ", ampl)
                    if ((mean < (target_mean - mean_tol_1)) | (mean > (target_mean + mean_tol_1))):
                        dac_step = int((target_mean -mean)/k1)
                        if dac_step > max_offset_dac_step: dac_step = max_offset_dac_step
                        if dac_step < -1*max_offset_dac_step: dac_step = -1*max_offset_dac_step
                        offset_dac_val += dac_step
                        if offset_dac_val > 1023: offset_dac_val = 1023
                        if offset_dac_val < 0: offset_dac_val = 0
                        dac_addr = 2*adc_chan + 1
                        print("Writing ", offset_dac_val, " to DAC ", dac_addr)
                        write_DAC_value(dac_addr, offset_dac_val)
                        mean_done = 0
                    else:
                        mean_done = 1
                    print()
                    print("Adjust gain DAC value for channel ", adc_chan)
                    val_list = []
                    get_samples(adc_chan, samples_2_get, val_list)
                    mean = sum(val_list)/len(val_list)
                    ampl = rms(val_list)
                    print("average value = ", mean, end = '')
                    print("  rms = ", ampl)
                    dB_dev = 20*np.log10(target_rms/ampl)
                    print(dB_dev)
                    #if ((ampl < (target_rms - rms_tol)) | (ampl > (target_rms + rms_tol))):
                    if (abs(dB_dev) > rms_tol):
                        dac_step = int(dB_dev/k2)
                        if dac_step > max_gain_dac_step: dac_step = max_gain_dac_step
                        if dac_step < -1*max_gain_dac_step: dac_step = -1*max_gain_dac_step
                        gain_dac_val += dac_step
                        if gain_dac_val > 1023: gain_dac_val = 1023
                        if gain_dac_val < 0: gain_dac_val = 0
                        dac_addr = 2*adc_chan + 2
                        print("Writing ", gain_dac_val, " to DAC ", dac_addr)
                        write_DAC_value(dac_addr, gain_dac_val)
                        gain_done = 0
                        mean_done = 0
                    else:
                        gain_done = 1
                        break
                    fhand.write(str(offset_dac_val) + "," + str(gain_dac_val) + "," + str(mean) + "," + str(ampl) + "\n")
                if ((gain_done & mean_done) == 1):
                    print()
                    print("Fine adjust offset DAC value for channel ", adc_chan)
            #Now a final fine adjust of the offset DAC
            mean_done = 0
            while (1):
                val_list = []
                get_samples(adc_chan, samples_2_get, val_list)
                mean = sum(val_list)/len(val_list)
                ampl = rms(val_list)
                print("average value = ", mean, end = '')
                print("  rms = ", ampl)
                if ((mean < (target_mean - mean_tol_2)) | (mean > (target_mean + mean_tol_2))):
                    dac_step = int((target_mean -mean)/k1)
                    #print("1 ", dac_step)
                    if dac_step > max_offset_dac_step: dac_step = max_offset_dac_step
                    #print("2 ", dac_step)
                    if dac_step < -1*max_offset_dac_step: dac_step = -1*max_offset_dac_step
                    #print("3 ", dac_step)
                    offset_dac_val += dac_step
                    if offset_dac_val > 1023: offset_dac_val = 1023
                    if offset_dac_val < 0: offset_dac_val = 0
                    dac_addr = 2*adc_chan + 1
                    print("Writing ", offset_dac_val, " to DAC ", dac_addr)
                    write_DAC_value(dac_addr, offset_dac_val)
                else:
                    mean_done = 1
                fhand.write(str(offset_dac_val) + "," + str(gain_dac_val) + "," + str(mean) + "," + str(ampl) + "\n")
                if (mean_done == 1):
                    print("Final DAC values: ", offset_dac_val, gain_dac_val)
                    offset_val[i]=offset_dac_val
                    gain_val[i]=gain_dac_val
                    break
        print("Mean Offset value with 50 runs  ",np.mean(offset_val))
        print("Mean Gain value with 50 runs  ",np.mean(gain_val))
        fhand.close()
            
        
        
            
        
    

        

            
            
