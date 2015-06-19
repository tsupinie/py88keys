
import numpy as np

class Speaker(object):
    def __init__(self):
        pass

    def updateSpeakerState(self, *args):
        pass

    def freqModulate(self, freq):
        return freq

    def ampModulate(self, amp):
        return amp

    def waveformModulate(self, waveform):
#       freq = np.fft.fftshift(np.fft.rfft(waveform, axis=1))
#       smooth_freq = np.concatenate((freq[:1, :], np.concatenate((freq[2:, :] + 2 * freq[1:-1, :] + freq[:-2, :], freq[-1:, :]))))
#       mod_waveform = np.fft.irfft(np.fft.ifftshift(smooth_freq), axis=0)
        return waveform # Return the waveform for now: need to check the above

class LeslieSpeaker(Speaker):
    _rot_speed = {
        'horn': { 'off':0., 'slow':0.8,  'fast':6.65 },
        'bass': { 'off':0., 'slow':0.65, 'fast':6.25 },
    }
    _rot_spinup = {
        'horn': 6.65 / 2.,
        'bass': 6.25 / 5.,
    }
    def __init__(self):
        self._angle = { 'horn':[ 0.], 'bass':[ 0.]}
        self._rotation = { 'horn':[ 0.], 'bass':[ 0.]}

        self._speed = 'off'
        self._crossover = 800.        

        self._secs = None

    def updateSpeakerState(self, size, sample_len):
        if self._secs is None:
            self._secs = sample_len * np.arange(size) / float(size)
        self._updateSpeaker('horn', size, sample_len)
        self._updateSpeaker('bass', size, sample_len)

    def _updateSpeaker(self, spkr, size, sample_len):
        seeking_spd = LeslieSpeaker._rot_speed[spkr][self._speed]
        cur_spd = self._rotation[spkr][-1]
        if cur_spd < seeking_spd:
            final_spd = min(cur_spd + LeslieSpeaker._rot_spinup[spkr] * sample_len, seeking_spd)
        else:
            final_spd = max(cur_spd - LeslieSpeaker._rot_spinup[spkr] * sample_len, seeking_spd)

        self._rotation[spkr] = np.interp(self._secs, [ 0, sample_len ], [cur_spd, final_spd])
        self._angle[spkr] = self._angle[spkr][-1] + np.add.accumulate(2 * np.pi * self._rotation[spkr] / (size / sample_len))[:, np.newaxis]

    def _getMagFreq(self, freq):
        spd_snd = 343.6
        spkr_bass_speed = 0

        if freq[0, 0] > self._crossover:
            spd_const = 2 * np.pi * 0.254 * 0.5
            spkr_speed = spd_const * self._rotation['horn'][:, np.newaxis]
            spkr_angle = self._angle['horn']
        else:
            spkr_speed = 0.
            spkr_angle = 0.
        return spd_snd / (spd_snd - spkr_speed * np.sin(spkr_angle))

    def _getMagAmp(self, freq):
#       spkr_rotation = np.where(freq > self._crossover, self._rotation['horn'][:, np.newaxis], self._rotation['bass'][:, np.newaxis])
#       norm = np.where(freq > self._crossover, LeslieSpeaker._rot_speed['horn']['fast'], LeslieSpeaker._rot_speed['bass']['fast'])
        return 0.25

    def setSpeed(self, speed):
        self._speed = speed

    def freqModulate(self, freq):
        mag_freq = self._getMagFreq(freq)
        mod_freq = mag_freq * freq
        return mod_freq

    def ampModulate(self, amp, freq):
        mag_amp = self._getMagAmp(freq) / 2.
        if freq[0, 0] > self._crossover:
            spkr_angle = self._angle['horn']
        else:
            spkr_angle = -self._angle['bass']
        
        mod_amp = (1 - mag_amp * (1 - np.cos(spkr_angle))) * amp
        return mod_amp
