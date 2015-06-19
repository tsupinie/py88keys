
import numpy as np

import pyaudio

import wave

class Tone(object):
    pitches = [ 'C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B' ]

    def __init__(self, pitch, gen_size, n_channels, bit_rate, speaker):
        self._pitch = pitch
        self._size = gen_size
        self._pitch_bend = 0
        self._last_pitch_bend = 0
        self._phase = np.zeros((n_channels, ))
        self._speaker = speaker

        self._has_cutoff = False
        self._is_finished = False

        self._n_channels = n_channels
        self._rate = bit_rate
        samples = np.arange(self._size)
        self._samples = samples[:, np.newaxis] + (np.arange(self._n_channels).T * 100)

    def setPitchBend(self, num_steps):
        self._pitch_bend = num_steps

    def cutoff(self):
        self._has_cutoff = True

    def generate(self):
        if not self._is_finished:
            if self._last_pitch_bend == self._pitch_bend:
                freq = Tone.pitch2Freq(self._pitch, self._pitch_bend) * np.ones((self._size, self._n_channels))
            else:
                freq = self.getFrequency()

            amp = self._speaker.ampModulate(np.ones((self._size, self._n_channels)), freq)
            freq = self._speaker.freqModulate(freq)

            dphase = 2 * np.pi * freq / self._rate
            phase = np.add.accumulate(dphase)
            audio = amp * np.sin(phase + self._phase)

            self._phase = (phase + self._phase)[-1]

            if self._has_cutoff:
                for ichn in xrange(self._n_channels):
                    zero_cross_idxs = np.where(audio[:-1, ichn] * audio[1:, ichn] <= 0)[0]
                    if len(zero_cross_idxs) > 0:
                        cutoff_idx = zero_cross_idxs[0]
                        audio[(cutoff_idx + 1):, ichn] = 0
                        self._is_finished = True

        else:
            audio = np.zeros((self._size, self._n_channels))

        self._last_pitch_bend = self._pitch_bend
        return audio

    def getFrequency(self):
        start_freq = Tone.pitch2Freq(self._pitch, self._last_pitch_bend)
        end_freq = Tone.pitch2Freq(self._pitch, self._pitch_bend)

        scale_fac = (end_freq / start_freq) ** (1. / (self._samples.shape[0] - 1))
        freq = start_freq * scale_fac ** self._samples
        return freq 

    def isFinished(self):
        return self._is_finished

    def __eq__(self, other):
        is_eq = False
        if type(other) == Tone:
            is_eq = (self._pitch == other._pitch)
        return is_eq

    def __neq__(self, other):
        return not self.__eq__(other)

    @staticmethod
    def intervalFromC0(pitch):
        if pitch[1] in [ '#', 'b' ]:
            note, octv = pitch[:2], int(pitch[2:])
        else:
            note, octv = pitch[:1], int(pitch[1:])

        return Tone.pitches.index(note) + len(Tone.pitches) * octv

    @staticmethod
    def intvC0ToPitch(interval):
        octave, note_idx = divmod(interval, len(Tone.pitches))
        return "%s%d" % (Tone.pitches[note_idx], octave)

    @staticmethod
    def pitch2Freq(pitch, bend=0):
        intv_a440 = Tone.interval('A4', pitch)
        return 440. * 2 ** ((intv_a440 + bend) / 12.)

    @staticmethod
    def interval(pitch_from, pitch_to):
        intv_from_c0 = Tone.intervalFromC0(pitch_from)
        intv_to_c0 = Tone.intervalFromC0(pitch_to)
        return intv_to_c0 - intv_from_c0

    @staticmethod
    def moveByInterval(pitch, interval):
        intv_c0 = Tone.intervalFromC0(pitch)
        return Tone.intvC0ToPitch(intv_c0 + interval)

class Note(object):
    def __init__(self, fundamental, harmonics, gen_size, n_channels, bit_rate, speaker):
        self._fund = fundamental
        self._harm = harmonics
        self._n_channels = n_channels
        self._bit_rate = bit_rate

        self._tones = []
        self._vols = []

        sum_loud = sum( 10 ** (h / 2.) for h in self._harm.values() )
        for intv, loud in self._harm.iteritems():
            harm_pitch = Tone.moveByInterval(self._fund, intv)
            self._tones.append(Tone(harm_pitch, gen_size, self._n_channels, self._bit_rate, speaker))
            self._vols.append( 10 ** (loud / 2.) / sum_loud)

    def getFundamental(self):
        return self._fund

    def setPitchBend(self, num_steps):
        for t in self._tones:
            t.setPitchBend(num_steps)

    def generate(self, size):
        chunks = [ t.generate() for t in self._tones ]
        return NoteGenerator.mix(chunks, self._vols, size, self._n_channels)

    def cutoff(self):
        for t in self._tones:
            t.cutoff()

    def isFinished(self):
        return all( t.isFinished() for t in self._tones )

    def __eq__(self, other):
        is_eq = False
        if type(other) == Note:
            is_eq = (self._fund == other._fund)
        return is_eq

    def __neq__(self, other):
        return not self.__eq__(other)

class NoteGenerator(object):
    def __init__(self, speaker, n_channels, bit_rate, max_pitch_bend, dtype=np.int16):
        self._speaker = speaker
        self._n_channels = n_channels
        self._dtype = dtype
        self._bit_rate = bit_rate
        self._master_volume = 0.25
        self._max_pitch_bend = max_pitch_bend

        self._harmonics = {0:1.}
        self._notes = []
        self._volumes = []
        self._wave_data = []

        self._gen_size = 1024

        self._pya = pyaudio.PyAudio()

        def grabMore(in_data, frame_count, time_info, status):
            data = self.generate(frame_count)
            return (data, pyaudio.paContinue)

        samp_width = self._dtype(1).itemsize

        self._stream = self._pya.open(format=self._pya.get_format_from_width(samp_width),
                    channels=n_channels,
                    rate=bit_rate,
                    output=True,
                    frames_per_buffer=self._gen_size,
                    stream_callback=grabMore)

        self._stream.start_stream()

    def cleanup(self):
        self._stream.stop_stream()
        self._stream.close()

        self._pya.terminate()

    def setTambre(self, harmonics):
        self._harmonics = harmonics

    def setVolume(self, volume):
        self._master_volume = volume

    def setPitchBend(self, amount):
        for n in self._notes:
            n.setPitchBend(amount * self._max_pitch_bend)

    def addNote(self, pitch, loudness):
        self._volumes.append(loudness)
        self._notes.append(Note(pitch, self._harmonics, self._gen_size, self._n_channels, self._bit_rate, self._speaker))

    def removeNote(self, pitch, loudness):
        remove_notes = [ n for n in self._notes if n.getFundamental() == pitch ]
        for n in remove_notes:
            n.cutoff()

    def generate(self, size=512):
        finished_notes = [ n for n in self._notes if n.isFinished() ]
        for n in finished_notes:
            self._volumes.remove(self._volumes[self._notes.index(n)])
            self._notes.remove(n)

        self._speaker.updateSpeakerState(size, float(size) / self._bit_rate)

        chunks = [ n.generate(size) for n in self._notes ]

        mixed = self._master_volume * NoteGenerator.mix(chunks, self._volumes, size, self._n_channels)
        mixed = self._speaker.waveformModulate(mixed)
        self._wave_data.append(mixed)
        rendered = NoteGenerator.render(mixed, self._dtype)
        return rendered

    def writeToFile(self, file_name):
        dat = NoteGenerator.render(np.concatenate(tuple(self._wave_data)), self._dtype)

        wf = wave.open(file_name, 'w')
        wf.setparams((self._n_channels, self._dtype(1).itemsize, self._bit_rate, 0, 'NONE', 'not compressed'))
        wf.writeframes(dat)
        wf.close()

    @staticmethod
    def mix(chunks, vols, size, n_channels):
        mixed = np.zeros((size, n_channels))
        for ch, vl in zip(chunks, vols):
            mixed += (vl * ch)
        return mixed

    @staticmethod
    def render(ary_data, dtype):
        n_samples = ary_data.shape[0] * ary_data.shape[1]

        dt_max = np.iinfo(dtype).max
        dt_min = np.iinfo(dtype).min

        dt_mag = (dt_max - dt_min + 1) / 2
        dt_off = dt_min + dt_mag
        dt_audio = (dt_mag * ary_data + dt_off).astype(dtype).flatten()

        data = str(dt_audio.tobytes())
        return data

if __name__ == "__main__":
    import pyaudio
    from time import sleep

    from speaker import LeslieSpeaker

    RATE = 44100
    RECORD_SECONDS = 5
    CHUNK = 128
    WIDTH = 2
    CHANNELS = 2

    tones = [ 'C2', 'C3', 'C4', 'E4', 'G4', 'Bb4' ]

    spkr = LeslieSpeaker()
    spkr.setSpeed('fast')
    gen = NoteGenerator(spkr, CHANNELS, RATE, 2)
    gen.setTambre({-12:0, 7:0, 0:0, 12:0, 19:0, 24:0, 28:0, 31:0, 36:0})

    note_idx = 0
    while True:
        try:
            sleep(1)
            if note_idx < len(tones):
                gen.addNote(tones[note_idx], 0.25)
                print Tone.pitch2Freq(tones[note_idx])
                note_idx += 1
            else:
                spkr.setSpeed('slow')
        except KeyboardInterrupt:
            print
            break

    print "done"

    gen.cleanup()
    gen.writeToFile("tones.wav")
