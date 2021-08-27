from collections import namedtuple
SAMP_FREQ = 16000.0
INPUT_FREQ = 16000.0
PEAK = 8 #peak for a 4-bit device is 8 (-8 to 7 range)
NUM_SAMPLES = 512*1024
run = namedtuple('sample',['date','board','channel','samplingfreq','signalfreq','rundata'])

