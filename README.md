# Py88Keys
A Python package for emulating common keyboard instrument sounds. You can either hook up a MIDI controller and play directly or write script to generate the tones. Currently emulates only a Hammond organ with a Leslie speaker.  Plans are to extend the package to analog synthesizer emulation. No GUI for now, though that may also change.

The MIDI driver was written for a M-Audio Keystation 88es. The USB library requires a vendor ID and product ID for whatever MIDI controller you're going to use. So if you're adapting this for some other controller, you'll need to find them.  I was able to do this on OS X Yosemite by plugging the controller into one of the USB ports, pulling up the System Information program and navigating to the "USB" section under "Hardware".  The controller should have its own entry, which lists the vendor and product IDs. I don't know how this would work on Windows or Linux.  I also don't know if other controllers will send over the same control sequences as mine.

### Prerequisites:
##### PyAudio (https://people.csail.mit.edu/hubert/pyaudio/)
This is used to talk to the sound card. I was able to install this using MacPorts, but I believe it's on Anaconda, too.

##### PyUSB (https://github.com/walac/pyusb)
This is used to interpret input from the MIDI controller, so if you're just scripting tones to play, you could probably get by without it. Again, I was able to install this using MacPorts.

### How to run:
`python midi_driver.py`

### How to change the drawbar setting (Hammond organ):
In `midi_driver.py`, there's a call to `gen.setTambre()`, which takes a dictionary.  The keys in the dictionary are the intervals from the fundamental (-12 is an octave below the fundamental, 19 is an octave and fifth above the fundamental, etc.), and the values are the volumes for each of those in decibels above peak.  Each stop on a Hammond drawbar represents ~3 dB change in volume; 8 (or full out) is 0 dB down, and 1 (almost all the way in) is -21 dB above peak, or 21 dB below peak.
