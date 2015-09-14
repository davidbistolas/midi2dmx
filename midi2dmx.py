#!/usr/bin/python
"""
midi2dmx - midi2dmx
davidbistolas
10/08/2015

<insert description here>

Copyright 2015 davidbistolas  
 

"""

__author__ = 'davidbistolas'
__appname__ = 'Midi2DMX'

# midi
from simplecoremidi import MIDIDestination

# OLA classes
from ola.ClientWrapper import ClientWrapper

# For OSX notification classes
import objc

# For OSX UI Stuff

import rumps

# base stuff
import itertools
import array
import threading


def split_seq(iterable, size):
    """Little hack to split iterables up"""
    it = iter(iterable)
    item = list(itertools.islice(it, size))
    while item:
        yield item
        item = list(itertools.islice(it, size))


class Midi2Dmx(threading.Thread):

    def __init__(self, driver_name="DMX Bridge", universe=0):
        """ midi->dmx bridge
        :param driver_name:  The midi name of the bridge. This will
                      show up in Logic
        :param universe:    The DMX universe to connect to
        """

        self.driver_name = driver_name
        self.appname = "{} - {}".format(__appname__, driver_name)
        # initialize a default dmx frame

        self.midi_source = MIDIDestination(driver_name)

        self.frame = [0] * 255
        self.universe = universe

        # this is the starting note for all midi channels
        self.note_offset = 24

        # this is the number of dmx channels per midi channel
        # each midi channel will support 32 notes. This will allow
        # 16 fixtures via 16 midi channels.
        self.dmx_offset = 32

        # MacOS X related stuff

        self.NSUserNotification = objc.lookUpClass('NSUserNotification')
        self.NSUserNotificationCenter = objc.lookUpClass('NSUserNotificationCenter')

        self.dmx_wrapper = None
        self.dmx_client = None
        self.dmx_tick = 100
        self.midi_tick = 10
        super(Midi2Dmx, self).__init__()

    def run(self):
        """Start up the service safely"""
        self.initialize()
        if self.dmx_wrapper:
            self.dmx_wrapper.Run()

    def stop(self):
        """Stop the service safely"""
        if self.dmx_wrapper:
            self.notify("Stopping...",
                        "Stopping the DMX Bridge. Midi Events "
                        "will NOT be sent to the DMX device")
            self.dmx_wrapper.Stop()
        else:
            self.notify("DMX is not running",
                        "Stop command issued to an inactive "
                        "DMX bridge.")

    def initialize(self):
        """
        Zero out dmx, set up events
        """
        try:
            self.dmx_wrapper = ClientWrapper()
            self.dmx_client = self.dmx_wrapper.Client()
        except:
            self.notify("OLAD is not running",
                        "Attept to connect to OLAD failed. "
                        "Please start it and try again.")
            return

        self.dmx_wrapper.AddEvent(self.dmx_tick, self.send_to_dmx)
        self.dmx_wrapper.AddEvent(self.dmx_tick/2, self.get_midi_data)


    def notify(self, subtitle, info_text):
        """Send an os x  notification"""
        title = "{} - Universe {}".format(self.appname, self.universe)
        rumps.notification(title,subtitle,info_text,sound=False)

    def dmx_frame_sent(self, state):
        """SendDMX callback"""
        if not state.Succeeded():
            self.dmx_wrapper.Stop()

    def send_to_dmx(self):
        """Send the frame to the uDMX device"""

        self.dmx_wrapper.AddEvent(self.dmx_tick, self.send_to_dmx)
        dmx_frame = self.build_dmx_frame()
        self.dmx_client.SendDmx(self.universe, dmx_frame, self.dmx_frame_sent)

    def update_frame(self, channel, note, velocity):
        """Translate midi note to dmx channel and
           velocity to value"""
        value = velocity * 2
        dmx_channel = (note - self.note_offset) + ((channel - 1) * self.dmx_offset)
        self.frame[dmx_channel] = value

    def build_dmx_frame(self):
        """Translate our internal frame structure into a proper dmx frame"""

        dmx_frame = array.array("B")
        for frame_channel in self.frame:
            dmx_frame.append(frame_channel)
        return dmx_frame

    def get_midi_data(self):
        """Get midi data from the midi source"""

        self.dmx_wrapper.AddEvent(self.dmx_tick, self.get_midi_data)
        midi_data = self.midi_source.recv()
        if len(midi_data) > 0:
            print midi_data
        for s in split_seq(midi_data, 3):
            self.parse_midi_data(s)


    def parse_midi_data(self, midi_data):
        """Parse the midi data"""

        # we're going to ignore non-note traffic
        # sysex data and such.
        note_on = False
        modifier = 0
        midi_channel = midi_data[0]


        if midi_channel in range(144, 159):
            modifier = 143
            note_on = True

        if midi_channel in range(128, 143):
            modifier = 127
            note_on = False

        if midi_channel in range(144, 159) or midi_channel in range(128, 143):

            channel = midi_channel - modifier
            note = midi_data[1]
            # make sure our velocity is '0' for the note-off
            # event.
            if note_on:
                velocity = midi_data[2]
            else:
                velocity = 0
            self.update_frame(channel, note, velocity)



class DmxBridge(rumps.App):

    def __init__(self, driver_name="DMX Bridge", universe=0):
        """ midi->dmx bridge
        :param driver_name:  The midi name of the bridge. This will
                      show up in Logic
        :param universe:    The DMX universe to connect to
        """

        self.driver_name = driver_name
        self.appname = "{} - {}".format(__appname__, driver_name)
        icon = None
        menu = ["Start Bridge", "Stop Bridge"]
        self.service = None
        super(DmxBridge, self).__init__(driver_name, driver_name, icon, menu, quit_button=None)


    @rumps.clicked("Start Bridge")
    def run_bridge(self, _):
        """ Starts up the bridge """
        self.service = Midi2Dmx()
        self.service.start()

    @rumps.clicked("Stop Bridge")
    def stop_bridge(self, _):
        """ Stops the bridge """
        if self.service:
            self.service.stop()

    @rumps.clicked("Exit")
    def quit_app(self, _):
        try:
            self.service.stop()
        except:
            pass
        rumps.quit_application()


if __name__ == '__main__':
    repeater = DmxBridge()
    repeater.run()
