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
from pyScore.util.range_checking import *
from midi_codes import *

from cStringIO import StringIO
try:
    import textwrap
except ImportError:
    from pyScore.util.backport import textwrap

# We try to do pretty religious range-checking below so the MIDI file is always
# valid, even if incorrect.

def get_channel(element, warnings):
   channel = int_range_check(
      element.get("Channel"), 1, 16,
      "<%s Channel='x'>" % element.tag, warnings)
   return channel - 1

class MidiXMLToMidi:
   def __init__(self):
      self._warnings = config.get("warnings")
      self._verbose = config.get("verbose")

   class State:
      def __init__(self):
         self.mode = "Delta"
         self.warnings = []
         
   def convert(self, tree, stream):
      # NOTE: Only type 1 MIDI files are supported at this time
      state = self.State()
      warnings = state.warnings
      self.make_midi_header(tree, stream, state)
      self.make_tracks(tree, stream.write, state)

      if self._warnings:
         for warning in warnings:
            print textwrap.fill("WARNING: " + warning)

   def make_midi_header(self, tree, stream, state):
      warnings = state.warnings
      midi_type = int_range_check(tree.findtext("./Format"), 0, 2,
                                  "<Format>", warnings)
      if midi_type < 0 or midi_type > 1:
         raise ValueError("Only type 0 and 1 MIDI files are supported at this time.")
      num_tracks = int_range_check(tree.findtext("./TrackCount"), 0, MAX_16_BIT,
                                   "<TrackCount>", warnings)
      ticks_per_beat = tree.findtext("./TicksPerBeat")
      if ticks_per_beat != None:
         ticks_per_beat = int_range_check(tree.findtext("./TicksPerBeat"), 0, MAX_16_BIT,
                                          "<TicksPerBeat>", warnings)
         ticks_per_beat = bin_number(ticks_per_beat, 2)
      else:
         frame_rate = int_range_check(tree.findtext("./FrameRate"), 0, 30,
                                      "<FrameRate>", warnings)
         ticks_per_frame = int_range_check(tree.findtext("./TicksPerFrame"), 0, MAX_7_BIT,
                                           "<TicksPerFrame>", warnings)
         ticks_per_beat = chr(0x80 + ord(bin_var_number(-frame_rate)[-1])) + chr(ticks_per_frame)
         
      state.mode = tree.findtext("./TimestampType")

      stream.write(''.join((
         FILE_HEADER,
         HEADER_LENGTH,
         bin_number(midi_type, 2),
         bin_number(num_tracks, 2),
         ticks_per_beat)))
   
   def make_tracks(self, tree, write, state):
      for track in tree.findall("./Track"):
         self.make_track(track, write, state)

   def make_track(self, track, write, state):
      data = StringIO()
      last_event_time = 0
      for event in track.findall("./Event"):
         element = event[-1]
         func_name = "event_%s" % element.tag.replace("-", "_")
         if hasattr(self, func_name):
            if state.mode == "Delta":
               delta = int(event.findtext("./Delta"))
            else:
               absolute = int(event.findtext("./Absolute"))
               delta = absolute - last_event_time
               last_event_time = absolute
            data.write(delta_time(delta))
            getattr(self, func_name)(element, data.write, state)
      data = data.getvalue()
      write(TRACK_HEADER)
      write(bin_number(len(data) + len(TRACK_END), 4))
      write(data)
      write(TRACK_END)

   ########################################
   # utility functions

   ########################################
   # Event types (handling the elements inside of <Event>)

   class VoiceEvent:
      def __init__(self, code, attributes):
         self._code = code
         self._attributes = attributes

      def __call__(self, element, write, state):
         channel = get_channel(element, state.warnings)
         write(chr(self._code + channel))
         for attr in self._attributes:
            val = int_range_check(element.get(attr), 0, 127,
                                  "<%s %s='x'>" % (element.tag, attr), state.warnings)
            write(chr(val))

   event_NoteOn = VoiceEvent(NOTE_ON, ("Note", "Velocity"))
   event_NoteOff = VoiceEvent(NOTE_OFF, ("Note", "Velocity"))
   event_PolyKeyPressure = VoiceEvent(AFTERTOUCH, ("Note", "Pressure"))
   event_ControlChange = VoiceEvent(CONTINUOUS_CONTROLLER, ("Control", "Value"))
   event_ProgramChange = VoiceEvent(PATCH_CHANGE, ("Number",))
   event_ChannelKeyPressure = VoiceEvent(CHANNEL_PRESSURE, ("Pressure",))

   class VoiceEventTwoBytes:
      def __init__(self, code):
         self._code = code

      def __call__(self, element, write, state):
         channel = get_channel(element, state.warnings)
         value = int_range_check(element.get("Value"), 0, MAX_14_BITS,
                                 "<%s Value='x'>" % element.tag, state.warnings)
         bytes = bin_var_number(value)
         if len(bytes) == 1:
            bytes = chr(0) + bytes
         write(chr(self._code + channel))
         write(bytes[1])
         write(bytes[0])

   event_PitchBendChange = VoiceEventTwoBytes(PITCH_BEND)

   class ModeEvent:
      def __init__(self, code):
         self._code = code

      def __call__(self, element, write, state):
         channel = get_channel(element, state.warnings)
         write(chr(CHANNEL_MODE + channel))
         write(chr(self._code))
         write("\0")

   event_AllSoundOff = ModeEvent(ALL_SOUND_OFF)
   event_ResetAllControllers = ModeEvent(RESET_ALL_CONTROLLERS)
   event_AllNotesOff = ModeEvent(ALL_NOTES_OFF)
   event_OmniOff = ModeEvent(OMNI_MODE_OFF)
   event_OmniOn = ModeEvent(OMNI_MODE_ON)
   event_PolyMode = ModeEvent(POLY_MODE_ON)

   class ModeEventBoolean:
      mapping = {"on": VALUE_ON,
                 "off": VALUE_OFF}
      def __init__(self, code):
         self._code = code

      def __call__(self, element, write, state):
         channel = get_channel(element, state.warnings)
         write(chr(CHANNEL_MODE + channel))
         write(chr(self._code))
         value = element.get("Value").lower()
         write(chr(self.mapping[value]))

   event_LocalControl = ModeEventBoolean(LOCAL_CONTROL_ONOFF)

   class ModeEventByte:
      def __init__(self, code):
         self._code = code

      def __call__(self, element, write, state):
         channel = get_channel(element, state.warnings)
         write(chr(CHANNEL_MODE + channel))
         write(chr(self._code))
         value = int_range_check(element.get("Value"), 0, 127,
                                 "<%s Value='x'>" % element.tag, state.warnings)
         write(chr(value))

   event_MonoMode = ModeEventByte(MONO_MODE_ON)
         
   class MetaEventBytes:
      def __init__(self, code, length, maximum):
         self._code = code
         self._length = length
         self._maximum = maximum
         
      def __call__(self, element, write, state):
         write(chr(META_EVENT))
         write(chr(self._code))
         # Really is a variable length quantity, but none of these
         # are very long, so we just do this, which is much faster
         write(chr(self._length))
         value = int_range_check(element.get("Value"), 0, self._maximum,
                                 "<%s Value='x'>" % element.tag, state.warnings)
         write(bin_number(value, self._length))

   event_SequenceNumber = MetaEventBytes(SEQUENCE_NUMBER, 2, MAX_16_BIT)
   event_MIDIChannelPrefix = MetaEventBytes(MIDI_CH_PREFIX, 1, MAX_4_BIT)
   event_SetTempo = MetaEventBytes(TEMPO, 3, MAX_24_BIT)
   event_Port = MetaEventBytes(MIDI_PORT, 1, MAX_7_BIT)

   class MetaEventText:
      def __init__(self, code):
         self._code = code

      def __call__(self, element, write, state):
         if element.text is not None: 
             write(chr(META_EVENT))
             write(chr(self._code))
             s = element.text.encode("ascii", "replace")
             write(bin_var_number(len(s)))
             write(s)

   event_TextEvent = MetaEventText(TEXT)
   event_CopyrightNotice = MetaEventText(COPYRIGHT)
   event_TrackName = MetaEventText(SEQUENCE_NAME)
   event_InstrumentName = MetaEventText(INSTRUMENT_NAME)
   event_Lyric = MetaEventText(LYRIC)
   event_Marker = MetaEventText(MARKER)
   event_CuePoint = MetaEventText(CUEPOINT)
   event_ProgramName = MetaEventText(PROGRAM_NAME)
   event_DeviceName = MetaEventText(DEVICE_NAME)

   class MetaEventData:
      def __init__(self, code):
         self._code = code

      def __call__(self, element, write, state):
         write(chr(META_EVENT))
         write(chr(self._code))
         s = hex_decode(element.text)
         write(bin_var_number(len(s)))
         write(s)

   event_SequencerSpecific = MetaEventData(SPECIFIC)

   def event_SMPTEOffset(self, element, write, state):
      write(chr(META_EVENT))
      write(chr(SMTP_OFFSET))
      write(chr(5))
      warnings = state.warnings
      hour = int_range_check(element.get("Hour"), 0, 23,
                             "<SMPTEOffset Hour='x'>", warnings)
      minute = int_range_check(element.get("Minute"), 0, 59,
                               "<SMPTEOffset Minute='x'>", warnings)
      second = int_range_check(element.get("Second"), 0, 59,
                               "<SMPTEOffset Second='x'>", warnings)
      frame = int_range_check(element.get("Frame"), 0, 29,
                              "<SMPTEOffset Frame='x'>", warnings)
      fractional_frame = int_range_check(element.get("FractionalFrame"), 0, 99,
                                         "<SMPTEOffset FractionalFrame='x'>", warnings)
      [write(chr(x)) for x in [hour, minute, second, frame, fractional_frame]]

   def event_TimeSignature(self, element, write, state):
      write(chr(META_EVENT))
      write(chr(TIME_SIGNATURE))
      write(chr(4))
      warnings = state.warnings
      numerator = int_range_check(
          element.get("Numerator"), 0, MAX_8_BIT,
          "<TimeSignature Numerator='x'>", warnings)
      denominator = int_range_check(
          element.get("LogDenominator"), 0, MAX_8_BIT,
          "<TimeSignature LogDenominator='x'>", warnings)
      clocks_per_metro = int_range_check(
          element.get("MIDIClocksPerMetronomeClick"), 0, MAX_15_BIT,
          "<TimeSignature MIDIClocksPerMetronomeClick='x'>", warnings)
      per_24_clocks = int_range_check(
          element.get("ThirtySecondsPer24Clocks"), 0, MAX_8_BIT,
          "<TimeSignature ThirtySecondsPer24Clocks='x'>", warnings)
      [write(chr(x)) for x in [numerator, denominator, clocks_per_metro, per_24_clocks]]

   def event_KeySignature(self, element, write, state):
      write(chr(META_EVENT))
      write(chr(KEY_SIGNATURE))
      write(chr(2))
      fifths = int_range_check(element.get("Fifths"), -7, 7,
                               "<KeySignature Fifths='x'>", state.warnings)
      mode = int_range_check(element.get("Mode"), 0, 1,
                             "<KeySignature Mode='x'>", state.warnings)
      write(bin_number(fifths, 1))
      write(chr(mode))

   def event_OtherMetaEvent(self, element, write, state):
      write(chr(META_EVENT))
      number = int_range_check(element.get("Number"), 0, MAX_7_BIT,
                               "<OtherMetaEvent Number='x'>", state.warnings)
      write(chr(number))
      s = hex_decode(element.text)
      write(bin_var_number(len(s)))
      write(s)

   def event_SystemExclusive(self, element, write, state):
      write(chr(SYSTEM_EXCLUSIVE))
      s = hex_decode(element.text)
      if not s.endswith(END_OF_EXCLUSIVE):
         s.append(END_OF_EXCLUSIVE)
      write(bin_var_number(len(s)))
      write(s)

   event_SysEx = event_SystemExclusive

   class ParameterNumber:
      def __init__(self, msb_num, lsb_num, msb_val, lsb_val, name):
         self._msb_num = msb_num
         self._lsb_num = lsb_num
         self._msb_val = msb_val
         self._lsb_val = lsb_val
         self._name = name
      
      def __call__(self, element, write, state):
         number = int_range_check(element.get(self._name), 0, MAX_14_BIT,
                                  "<%s %s='x'>" % (element.tag, self.name), state.warnings)
         value = int_range_check(element.get("Value"), 0, MAX_14_BIT,
                                 "<%s Value='x'>" % element.tag, state.warnings)
         number = bin_var_number(number)
         value = bin_var_number(value)
         if len(number) > 1:
            write(chr(CONTINUOUS_CONTROLLER + int(state.channel)))
            write(chr(self._msb_num))
            write(number[0])
         # We need to write another zero delta-time here
         write(delta_time(0))
         write(chr(CONTINUOUS_CONTROLLER + int(state.channel)))
         write(chr(self._lsb_num))
         write(numer[-1])

         if len(value) > 1:
            write(delta_time(0))
            write(chr(CONTINUOUS_CONTROLLER + int(state.channel)))
            write(chr(self._msb_val))
            write(value[0])
         write(delta_time(0))
         write(chr(CONTINUOUS_CONTROLLER + int(state.channel)))
         write(chr(self._lsb_val))
         write(value[-1])

   event_RPNChange = ParameterNumber(101, 100, 6, 38, "RPN")
   event_NRPNChange = ParameterNumber(99, 98, 6, 38, "NRPN")

   def event_ControlChange14(self, element, write, state):
      channel = get_channel(element, state.warnings)
      write(chr(CONTINUOUS_CONTROLLER + channel))
      number = int_range_check(element.get("Number"), 0, 127,
                               "<ControlChange14 Number='x'>", state.warnings)
      value = int_range_check(element.get("Value"), 0, MAX_14_BIT,
                              "<ControlChange14 Value='x'>", state.warnings)
      bytes = bin_var_number(value)
      if len(bytes) == 1:
         bytes = chr(0) + bytes
      write(chr(number))
      write(bytes[0])
      write(delta_time(0))
      write(chr(CONTINUOUS_CONTROLLER + channel))
      write(chr(number + 0x20))
      write(bytes[1])

   # NOTE: MidiXML <EndOfTrack> elements are ignored
   # NOTE: MidiXML <MTCQuarterFrame> elements are ignored

__all__ = """
MidiXMLToMidi
""".split()

