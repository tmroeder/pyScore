"""
Code to convert from MidiXML to MIDI
Python GUIDO tools

Copyright (C) 2004 Michael Droettboom
"""
## This program is free software; you can redistribute it and/or
## modify it under the terms of the GNU General Public License
## as published by the Free Software Foundation; either version 2
## of the License, or (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
 
## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.

from pyScore.config import config
from pyScore.elementtree.ElementTree import Element, SubElement, tostring
from pyScore.MIDI.conversion_constants import *
from midi_codes import *

from cStringIO import StringIO


# TODO: Midi XML -> MIDI could be done more efficiently (perhaps) with a SAX-like parser

class MidiXMLToMidi:
   def __init__(self):
      self._warnings = config.get("warnings")
      self._verbose = config.get("verbose")

   class State:
      def __init__(self, mode="Delta"):
         self.mode = mode

   def convert(self, tree, stream):
      # NOTE: Only type 1 MIDI files are supported at this time
      midi_type = int(tree.findtext("./Format"))
      if midi_type != 1:
         raise ValueError("Only type 1 MIDI files are supported at this time.")
      num_tracks = int(tree.findtext("./Tracks"))
      ticks_per_beat = int(tree.findtext("./TicksPerBeat"))
      state = self.State(tree.findtext("./TimestampType"))
      
      stream.write(self.make_midi_header(midi_type, num_tracks, ticks_per_beat))
      self.make_tracks(tree, stream, state)

   def make_midi_header(self, type, num_tracks, ticks_per_beat):
      return ''.join((
            FILE_HEADER,
            HEADER_LENGTH,
            bin_number(type, 2),
            bin_number(num_tracks, 2),
            bin_number(ticks_per_beat, 2)))
      
   def make_tracks(self, tree, stream, state):
      for track in tree.findall("./Track"):
         self.make_track(track, stream, state)

   def make_track(self, track, stream, state):
      data = StringIO()
      last_event_time = 0
      for event in track.findall("./Event"):
         if state.mode == "Delta":
            delta = int(event.findtext("./Delta"))
         else:
            absolute = int(event.findtext("./Absolute"))
            delta = absolute - last_event_time
            last_event_time = absolute
         data.write(delta_time(delta))
         self.dispatch_event(event[-1], data, state)
      data = data.getvalue()
      stream.write(TRACK_HEADER)
      stream.write(bin_number(len(data) + len(TRACK_END), 4))
      stream.write(data)
      stream.write(TRACK_END)

   simple_events = {"NoteOn": (NOTE_ON, "./Note", "./Velocity"),
                    "NoteOff": (NOTE_OFF, "./Note", "./Velocity"),
                    "PolyKeyPressure": (AFTERTOUCH, "./Note", "./Pressure"),
                    "ControlChange": (CONTINUOUS_CONTROLLER, "./Control", "./Value"),
                    "ProgramChange": (PATCH_CHANGE, "./Number"),
                    "ChannelKeyPressure": (CHANNEL_PRESSURE, "./Pressure"),
                    "PitchBendChange": (PITCH_BEND, "./Value", "MSB")}

   def dispatch_event(self, element, stream, state):
      if self.simple_events.has_key(element.tag):
         handles = self.simple_events[element.tag]
         stream.write(chr(handles[0] + int(element.findtext("./Channel"))))
         if len(handles) > 2:
            if handles[2] == "MSB":
               stream.write(bin_number(element.findtext(handles[1]), 2))
            else:
               stream.write(chr(int(element.findtext(handles[1]))))
               stream.write(chr(int(element.findtext(handles[2]))))
         else:
            stream.write(chr(int(element.findtext(handles[1]))))
      else:
         func_name = "event_%s" % element.tag.replace("-", "_")
         if hasattr(self, func_name):
            return getattr(self, func_name)(element, stream, state)
      return None

