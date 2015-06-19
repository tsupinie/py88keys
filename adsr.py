
import numpy as np

class ADSR(object):
    def __init__(self, attack, decay, sustain, release):
        self._attack_time = attack
        self._decay_time = decay
        self._sustain_amp = sustain
        self._release_time = release

        self._ads_time = [0, self._attack_time, self._attack_time + self._decay_time]
        self._ads_amp = [0, 1., self._sustain_amp]

    def envelope(self, time_since_pressed, time_since_released, len_sample, size):
        env = np.empty((size, ))
        secs = np.linspace(0, len_sample, size)

        if time_since_released >= 0:
            secs += time_since_pressed
            time_of_release = time_since_pressed - time_since_released
            env_at_release = np.interp([time_of_release], self._ads_time, self._ads_amp)
            env[:] = np.interp(secs, [ time_of_release, time_of_release + self._release_time ], [ env_at_release, 0 ])
        else:
            secs += time_since_pressed
            env[:] = np.interp(secs, self._ads_time, self._ads_amp)

        return env

if __name__ == "__main__":
    import matplotlib
    matplotlib.use('agg')
    import pylab

    adsr = ADSR(0.1, 0.1, 0.7, 0.2)

    secs = 1
    bit_rate = 44100
    size = 1024
    samples_created = 0

    envelope = []
    time = []

    release_time = 0.8

    for idx in xrange(secs * bit_rate / size):
        if float(samples_created) / bit_rate > release_time:
            release = float(samples_created) / bit_rate - release_time
        else:
            release = -1

        env = adsr.envelope(float(samples_created) / bit_rate, release, float(size) / bit_rate, size)

        time.extend(np.arange(samples_created, samples_created + size, dtype=np.float64) / bit_rate)
        envelope.extend(env)

        samples_created += size

    pylab.figure()
    pylab.plot(time, envelope)
    pylab.grid()
    pylab.savefig('env_test.png')
