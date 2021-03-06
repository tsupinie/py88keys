
import usb.core

from tonegen import NoteGenerator
from speaker import LeslieSpeaker 

import sys

def playNote(gen, keyNum, loudness):
    pitches = ['C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B' ]
    base = 24
    
    octave, pitch = divmod(keyNum - base, len(pitches))
    note = "%s%d" % (pitches[pitch], octave)
    if loudness > 0:
        gen.addNote(note, loudness / 128.)
    else:
        gen.removeNote(note, loudness / 128.)

def changeVolume(gen, level):
    gen.setVolume(level / 128.)

def changeModulation(speaker, mod_amount):
    if isinstance(speaker, LeslieSpeaker):
        if mod_amount / 128. < 0.3333:
            speaker.setSpeed('off')
        elif mod_amount / 128. < 0.66666:
            speaker.setSpeed('slow')
        else:
            speaker.setSpeed('fast')

def pitchBend(gen, amount):
    gen.setPitchBend((amount - 64) / 64.)

def handleInput(generator, speaker, sequence):
    control = list(sequence)[:2]

    if control == [9, 144]:
        keyNum, loudness = sequence[2:]
        playNote(generator, keyNum, loudness)
    elif control == [ 11, 176 ]:
        mod_control = sequence[2]
        if mod_control == 1:
            changeModulation(speaker, sequence[-1])
        elif mod_control == 7:
            changeVolume(generator, sequence[-1])
        else:
            print "Unrecognized modulation control code:", mod_control
    elif control == [ 14, 224 ]:
        bend_amount = sequence[3]
        pitchBend(generator, bend_amount)
        pass
    else:
        print "Unrecognized control sequence:", sequence

class find_class(object):
    def __init__(self, class_):
        self._class = class_

    def __call__(self, device):
        # first, let's check the device
        if device.bDeviceClass == self._class:
            return True
        # ok, transverse all devices to find an
        # interface that matches our class
        for cfg in device:
            # find_descriptor: what's it?
            intf = usb.util.find_descriptor(cfg, bInterfaceClass=self._class)
            if intf is not None:
                return True

        return False

def setupUSB():
    devs = usb.core.find(find_all=True, custom_match=find_class(1))

    if devs == []:
        print "USB device with vendor id 0x%x and product id 0x%x not found!" % (vendor_id, prod_id)
        sys.exit()

    for dev in devs:
        dev.set_configuration()

        intf = dev[0][1, 0]

        rd_endpoint_addr = intf[0].bEndpointAddress
        wt_endpoint_addr = intf[1].bEndpointAddress

        dev.read_ = dev.read
        dev.write_ = dev.write

        dev.read = lambda nb: dev.read_(rd_endpoint_addr, nb, interface=intf, timeout=999999)
        dev.write = lambda nb: dev.write_(wt_endpoint_addr, nb, interface=intf, timeout=999999)

    # Just return the first one for now; have to think about how to do multiple devices at the same time.
    return devs[0]

def main():
    if len(sys.argv) > 1:
        wav_file = sys.argv[1]
    else:
        wav_file = None

    n_channels = 2
    bit_rate = 44100
    max_pitch_bend = 2

    usb_dev = setupUSB()

    speaker = LeslieSpeaker()
    gen = NoteGenerator(speaker, n_channels, bit_rate, max_pitch_bend)

    gen.setTambre({
        -12:0, 
        7:0,
        0:0,
        12:-100,
        19:-100,
        24:-100,
        28:-100,
        31:-100,
        36:-100,
    })

    while True:
        try:
            seq = usb_dev.read(4)
            handleInput(gen, speaker, seq)
        except KeyboardInterrupt:
            print 
            break

    print "Cleaning up ..."
    gen.cleanup()

    if wav_file is not None:
        gen.writeToFile(wav_file)
    return

if __name__ == "__main__":
    main()
