import pyaudio
import numpy as np
import wave
import math
import random

from time import sleep

import pylab as pl

random.seed()

CHUNK = 256
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 48000
MAX_AMP = 2**15 - 1


class Audio(pyaudio.PyAudio):

    def __init__(self, channels=1,
                 rate=RATE,
                 chunk=CHUNK,
                 format=FORMAT):
        pyaudio.PyAudio.__init__(self)

        self.chan = channels
        self.rate = rate
        self.chunk = chunk
        self.format = format
        self.nptype = self.get_np_type(format)

        self.data = np.array([], dtype=self.nptype)
        
        self.istream = None
        self.ostream = None

        self.chunk_index = 0

    def __del__(self):
        self.terminate()

    def get_chunk(self):
        tmpstr = self.istream.read(self.chunk)
        array = np.fromstring(tmpstr, dtype=self.nptype)
        self.data = np.append(self.data, array)
        
    def put_chunk(self):
        slice_from = self.chunk_index*self.chunk
        slice_to = min(self.data.shape[0], slice_from + self.chunk)

        if slice_from > self.data.shape[0]:
            raise IndexError
        array = self.data[slice_from:slice_to]
        self.ostream.write(array.tostring())
        self.chunk_index += 1
        
    def open_input_stream(self):
        self.istream = self.open(format=self.format,
                                 channels=self.chan,
                                 rate=self.rate,
                                 input=True,
                                 frames_per_buffer=self.chunk)
   
    def close_input_stream(self):
        self.istream.close()
        self.istream = None
      
    def open_output_stream(self):
        self.ostream = self.open(format=self.format,
                                 channels=self.chan,
                                 rate=self.rate,
                                 output=True)
        self.chunk_index = 0
                
    def close_output_stream(self):
        self.ostream.close()
        self.ostream = None

    def record(self, time=5.0):
        self.data = np.array([], dtype=self.nptype)
        self.open_input_stream()
        print("Recording...")
        for i in range(0, int(time * self.rate/self.chunk)):
            self.get_chunk()
        print("Done Recording")
        self.close_input_stream()

    def play(self):
        self.open_output_stream()
        self.chunk_index = 0
        print("Playing...")
        while True:
            try:    
                self.put_chunk()
            except IndexError:
                break
        
        sleep(0.4) 
        self.close_output_stream()

    def save(self, path):
        raw = self.data.tostring()
        wf = wave.open(path, 'wb')
        wf.setnchannels(self.chan)
        wf.setsampwidth(self.get_sample_size(self.format))
        wf.setframerate(self.rate)
        wf.writeframes(raw)
        wf.close()

    def load(self, path):
        wf = wave.open(path, "rb")
        self.format = self.get_format_from_width(wf.getsampwidth())
        self.nptype = self.get_np_type(self.format)
        self.chan = wf.getnchannels()
        self.rate = wf.getframerate()
        self.data = np.array([], dtype=self.nptype)
        raw = wf.readframes(self.chunk)
        while raw:
            array = np.fromstring(raw, dtype=self.nptype)
            self.data = np.append(self.data, array)
            raw = wf.readframes(self.chunk)
        wf.close()
    
    def get_np_type(self, type):
        if type == pyaudio.paInt16:
            return np.int16
    
    def get_pa_type(self, type):
        if type == np.int16:
            return pyaudio.paInt16
    
    def add_echo(self, repeat, delay):
        length = self.data.shape[0]
        array = np.zeros(length + repeat*delay, dtype=np.float)

        for i in range(0, repeat+1):
            start = i*delay
            end = length + i*delay
            scale = 2**(i+1)
            array[start:end] += self.data / scale
        self.data = np.rint(array).astype(self.nptype)

    def rescale(self, val):
        if not 0 <= val <= 1:
            raise ValueError("Expected scaling factor between 0 and 1")
            
        peak = np.max(np.abs(self.data))

        rescale_factor = val*MAX_AMP/peak

        self.data = (self.data * rescale_factor).astype(self.nptype)

    def create_tone(self, frequency, length, amplitude):
        if not 0 <= amplitude <= 1:
            raise ValueError("Expected amplitude between 0 and 1")
            
        s = np.zeros(length, self.nptype)

        for i in range(0, length):
            s[i] = amplitude * MAX_AMP \
                   * math.sin(frequency * i * 2 * math.pi/self.rate)

        self.data = s

    def create_noise(self, length, amplitude):

        if not 0 <= amplitude <= 1:
            raise ValueError("Expected amplitude between 0 and 1")

        s = np.zeros(length, self.nptype)

        for i in range(0, length):
            s[i] = amplitude * MAX_AMP * random.random()

        self.data = s


    def add(self, other):
        length = max(self.data.shape[0], other.data.shape[0])
        array = np.zeros(length, dtype=self.nptype)
        array += self.data / 2.0
        array += other.data / 2.0
        self.data = array

    def __len__(self):
        return self.data.shape[0]

    def get_samplerange(self):
        if self.nptype == np.int16:
            return math.pow(2, 16)

    def compute_fft(self, start, end):
        dur = end - start
        fft = pl.fft(self.data[start:end])
        real_range = np.ceil((dur+1)/2.0)
        fft = fft[0:real_range]
        fft = abs(fft)

        return fft * np.hanning(len(fft))

    def change_speed(self, factor):
        indxs = np.round(np.arange(0, len(self.data), factor))
        indxs = indxs[indxs < len(self.data)].astype(int)
        self.data = self.data[indxs]

    def time_stretch_fft(self, factor, windowsize=1024, overlap=512, apply_hanning=True):
        phase = np.zeros(windowsize)
        if apply_hanning:
            amp_window = np.hanning(windowsize)
        else:
            amp_window = np.ones(windowsize, dtype=np.float)
        result = np.zeros(int(len(self.data) / factor + windowsize))

        for i in np.arange(0, len(self.data)-(windowsize+overlap), overlap*factor, dtype=np.int):
            a1 = self.data[i: i + windowsize]
            a2 = self.data[i + overlap: i + windowsize + overlap]

            s1 = np.fft.fft(amp_window * a1)
            s2 = np.fft.fft(amp_window * a2)
            phase = (phase + np.angle(s2/s1)) % 2*np.pi
            a2_rephased = np.fft.ifft(np.abs(s2)*np.exp(1j*phase))

            i2 = int(i/factor)
            result[i2:i2 + windowsize] += amp_window*np.real(a2_rephased)
        result = ((2**(16-4)) * result/result.max())

        self.data = result.astype(self.nptype)

    def plot_waveform(self, start=0, end=-1, x_unit="samples"):
        array = self.data[start:end]
        num_samples = len(array)
        if x_unit == "samples":
            pl.plot(range(num_samples), array)
            pl.xlabel('Time (Samples)')
        elif x_unit == "time":
            end_time = self.samples_to_time(num_samples)
            y_steps = np.arange(0, end_time, float(end_time) / num_samples)
            pl.plot(y_steps, array)
            pl.xlabel('Time (s)')
        pl.ylabel('Amplitude')
        samplerange = self.get_samplerange()
        pl.ylim([-samplerange/2, samplerange/2])
        pl.show()

    def plot_spectrum(self, array, start=0, end=-1, plot_log=False):
        array = array[start:end]
        len_arr = len(array)
        freq_axis = np.arange(0, len_arr, 1.0)  # * (self.rate / len_arr)
        if plot_log:
            pl.plot(freq_axis/1000, 10*np.log10(array), color='k')
            pl.ylabel('Power (dB)')
        else:
            pl.plot(freq_axis/1000, array, color='k')
        pl.xlabel('Frequency (kHz)')
        pl.show()


def sum_audio(audio_objects):
    length = len(max(audio_objects, key=len))
    scale = 1.0/len(audio_objects)

    array = np.zeros(length, dtype=np.int16)
    
    for obj in audio_objects:
        array += np.rint(obj.data * scale).astype(np.int16)
    
    new_object = Audio()
    new_object.data = array
    
    return new_object


def test_add():
    c = Audio()
    e = Audio()
    g = Audio()

    c.create_tone(261.63, 240000, 0.8)
    e.create_tone(329.63, 240000, 0.8)
    g.create_tone(392.00, 240000, 0.8)
     
    chord = sum_audio((c, e, g))
        
    chord.play()

if __name__ == "__main__":
    d = Audio()
    d.load('kdt48.wav')
    d.time_stretch_fft(0.9, 4096, 256)
    d.play()
