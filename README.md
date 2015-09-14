# midi2dmx
Simple Python MacOS X Toolbar app that allows you to run uDMX sequences via Midi. Useful if you use a DAW type app to run your band's backing tracks like we do.

To build: run python ./setup.py py2app --iconfile ./levels.icns

This will create an app in ./dist/ called midi2dmx.app 

REQUIRES: OLA, simplecoremidi and a uDMX USB Dongle. 

Input: MIDI - 16 channels, 32 DMX channes per Midi Channel, starting at note #24 (Middle C). 

Each note activiates a DMX Channel, the note's velocity is the 'value' for that dmx frame. 
