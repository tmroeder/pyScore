"""
Code to convert from MusicXML to MidiXML
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
from pyScore.MIDI.midi_codes import *
from pyScore.util.range_checking import *


from math import log
try:
   import textwrap
except ImportError:
   from pyScore.util.backport import textwrap

config.add_option("", "--divisions", action="store", default=DIVISIONS, type="int")
config.add_option("", "--ticks-per-beat", type="int", default=TICKS_PER_BEAT,
                  help="[midi] The number of MIDI ticks per quarter note when outputting MidiXML")
config.add_option("", "--midi-format", type="int", default=1,
                  help="[midi] The Midi file type (must be either 0 or 1)")

def make_event(subevent, time_spine, ticks_per_quarter_note):
   event = Element("Event")
   SubElement(event, "Absolute").text = str(int(time_spine))
   event.time_spine = time_spine
   event.append(subevent)
   return event

class MusicXMLToMidiXML:
   def __init__(self, ticks_per_beat=TICKS_PER_BEAT):
      self._ticks_per_beat = config.get("ticks_per_beat")
      self._warnings = config.get("warnings")
      self._verbose = config.get("verbose")
      self._divisions = config.get("divisions")

   class State:
      def __init__(self):
         self.format = 1
         self.part_no = 0
         self.channel = 1
         self.used_channels = {}
         self.dynamics = 64
         self.warnings = []

   ########################################
   # utility methods

   def dispatch_element(self, element, time_spine, events, meta_events, state):
      """Given a MusicXML element <x>, dispatches a call to a method named element_x"""
      func_name = "element_%s" % element.tag.replace("-", "_")
      if hasattr(self, func_name):
         return getattr(self, func_name)(element, time_spine, events, meta_events, state)
      return None

   def convert_duration(self, duration, divisions):
      return float(duration) / float(divisions) * float(self._ticks_per_beat)

   def make_control_change14(self, msb_number, value, time_spine, state):
      value = int_range_check(value, 0, MAX_14_BIT, "Controller %d" % msb_number, state.warnings)
      control14 = Element("ControlChange14",
                          Channel = str(state.channel),
                          Number = str(msb_number),
                          Value = str(value))
      return make_event(control14, time_spine, state.ticks_per_beat)

   def make_control_change(self, number, value, time_spine, state):
      value = int_range_check(value, 0, MAX_7_BIT, "Controller %d" % number, state.warnings)
      control = Element("ControlChange",
                        Channel = str(state.channel),
                        Number = str(number),
                        Value = str(value))
      return make_event(control, time_spine, state.ticks_per_beat)

   def element_recurse(self, direction, time_spine, events, meta_events, state):
      for element in direction:
         self.dispatch_element(element, time_spine, events, meta_events, state)

   ########################################
   # Top-level methods
      
   def convert(self, music_xml):
      state = self.State()
      state.ticks_per_beat = self._ticks_per_beat
      midi = Element("MIDIFile")
      state.format = config.get("midi_format")
      SubElement(midi, "Format").text = str(state.format)
      num_tracks = len(music_xml.findall("./part-list//score-part"))
      if num_tracks > 16:
         raise ValueError("Too many tracks to convert to MIDI (for now, at least).")
      # We always create a meta-track, so the number of tracks is actually len + 1
      SubElement(midi, "TrackCount").text = str(num_tracks + 1)
      SubElement(midi, "TicksPerBeat").text = str(state.ticks_per_beat)
      SubElement(midi, "TimestampType").text = "Absolute"
      self.get_measure_lengths(music_xml, state)
      self.make_tracks(music_xml, midi, state)
      if self._warnings:
         for warning in state.warnings:
            print textwrap.fill("WARNING: " + warning)
      return midi

   def get_measure_lengths(self, music_xml, state):
      measure_lengths = {}
      for part in music_xml.findall("./part"):
         time_spine = 0
         duration = 0
         for measure in part:
            measure_no = measure.attrib["number"]
            measure_lengths.setdefault(measure_no, 0)
            for element in measure:
               if element.find("./chord") is None:
                  time_spine += duration

               if element.tag == "attributes":
                  state.divisions = element.findtext("./divisions") or state.divisions

               duration = int(element.findtext("./duration") or "0")
               if duration != None:
                  duration = self.convert_duration(duration, state.divisions)
               
               if element.tag == "backup":
                  time_spine -= duration
                  duration = 0
               elif element.tag == "forward":
                  time_spine += duration
                  duration = 0
               else:
                  measure_lengths[measure_no] = max(measure_lengths.get(measure_no, 0), time_spine + duration)
               measure_lengths[measure_no] = max(measure_lengths.get(measure_no, 0), time_spine)

            time_spine += duration
            duration = 0
            measure_lengths[measure_no] = max(measure_lengths.get(measure_no, 0), time_spine)
      state.measure_lengths = measure_lengths

   def make_tracks(self, music_xml, midi, state):
      state.part_no = 0
      meta_track = SubElement(midi, "Track", Number=str(state.part_no))
      meta_events = []

      for toplevel in (music_xml.find("./work"), music_xml.find("./identification")):
         for element in toplevel:
            self.dispatch_element(element, 0, meta_events, meta_events, state)

      for i, (part, score_part) in enumerate(zip(music_xml.findall("./part"),
                                                 music_xml.findall("./part-list//score-part"))):
         state.part_no = i + 1
         self.make_track(part, score_part, midi, meta_events, state)

      meta_events.sort(lambda x, y: cmp(x.time_spine, y.time_spine))
      for event in meta_events:
         meta_track.append(event)

   def make_track(self, part, score_part, midi, meta_events, state):
      time_spine = 0
      duration = 0
      if state.format == 1:
         events = []
      else:
         events = meta_events
      state.channel = state.part_no 
      state.dynamics = 64
      for element in score_part:
         self.dispatch_element(element, time_spine, events, meta_events, state)

      # When figuring out the absolute time of events, we stay in the MusicXML domain
      # (DIVISIONS) until we write out (TICKS_PER_BEAT).  This prevents rounding error
      # from accumulating as durations are summed together, particularly since you
      # have to use such low numbers for TicksPerBeat in the MIDI spec.
      for measure in part:
         measure_no = measure.attrib["number"]
         for element in measure:
            if element.find("./chord") is None:
               time_spine += duration

            if element.tag == "attributes":
               state.divisions = element.findtext("./divisions") or state.divisions

            duration = int(element.findtext("./duration") or "0")
            if duration != None:
               duration = self.convert_duration(duration, state.divisions)
               
            if element.tag == "backup":
               time_spine -= duration
               duration = 0
            elif element.tag == "forward":
               time_spine += duration
               duration = 0
            else:
               self.dispatch_element(element, time_spine, events, meta_events, state)
         time_spine = state.measure_lengths[measure_no]
         duration = 0

      if element.find("./chord") is None:
         time_spine += duration

      if state.format == 1:
         events.sort(lambda x, y: cmp(x.time_spine, y.time_spine))
         track = SubElement(midi, "Track", Number=str(state.part_no))
         for event in events:
            track.append(event)

   ########################################
   # Concrete elements

   element_attributes = element_direction = element_direction_type = element_recurse
   element_score_instrument = element_recurse

   class MetaText:
      def __init__(self, name):
         self._name = name

      def __call__(self, input, time_spine, events, meta_events, state):
         output = Element(self._name)
         output.text = input.text[:]
         meta_events.append(make_event(output, time_spine, state.ticks_per_beat))

   element_rights = MetaText("CopyrightNotice")
   element_work_title = MetaText("TextEvent")
   element_words = MetaText("TextEvent")
   element_rehearsal = MetaText("Marker")

   def element_creator(self, input, time_spine, events, meta_events, state):
      output = Element("TextEvent")
      output.text = input.get("type") + ": " + input.text
      meta_events.append(make_event(output, time_spine, state.ticks_per_beat))

   class Text:
      def __init__(self, name):
         self._name = name

      def __call__(self, input, time_spine, events, meta_events, state):
         output = Element(self._name)
         output.text = input.text[:]
         events.append(make_event(output, time_spine, state.ticks_per_beat))

   element_part_name = Text("TrackName")
   element_instrument_name = Text("InstrumentName")
      
   def element_midi_instrument(self, midi_inst, time_spine, events, meta_events, state):
      state.channel = midi_inst.findtext("./midi-channel") or state.channel
      name = midi_inst.findtext("./midi-name")
      if name != None:
         program_name = Element("ProgramName")
         program_name.text = name
         events.append(make_event(program_name, time_spine, state.ticks_per_beat))
      bank = midi_inst.findtext("./midi-bank")
      if bank != None:
         self.make_control_change14(bank, BANK_SELECT_MSB, time_spine, state)
      program = midi_inst.findtext("./midi-program")
      if program != None:
         program_change = Element("ProgramChange",
                                  Channel = str(state.channel),
                                  Number = program)
         events.append(make_event(program_change, time_spine, state.ticks_per_beat))

   def element_note(self, note, time_spine, events, meta_events, state):
      if note.find("./rest") is None and note.find("./grace") is None:
         duration = int(note.findtext("./duration") or "0")

         lyric = note.find("./lyric")
         if lyric != None:
            self.element_lyric(lyric, time_spine, events, meta_events, state)

         pitch = note.find("./pitch")
         pitch_name = pitch.findtext("./step")
         alter = int(pitch.findtext("./alter") or "0")
         octave = int(pitch.findtext("./octave") or "3")
         midi_number = int_range_check(
            pitch_names_to_semitones[pitch_name] + alter + (octave + 1) * 12,
            0, MAX_7_BIT, "Note value", state.warnings)

         note_on = Element("NoteOn",
                           Channel = str(state.channel),
                           Note = str(midi_number),
                           Velocity = str(state.dynamics))
         events.append(make_event(note_on, time_spine, state.ticks_per_beat))
         
         note_off = Element("NoteOff",
                            Channel = str(state.channel),
                            Note = str(midi_number),
                            Velocity = "0")
         events.append(
            make_event(note_off,
                       int(time_spine + max(0, self.convert_duration(duration, state.divisions) - 1)),
                       state.ticks_per_beat))

   def element_lyric(self, lyric, time_spine, events, meta_events, state):
      # NOTE: Lyric syllables from MusicXML -> MidiXML are pretty weak for obvious reasons
      syllable = lyric.findtext("./text")
      syllabic = lyric.findtext("./syllabic")
      if syllabic in ("begin", "middle"):
         syllable += "-"
      output = Element("Lyric")
      output.text = syllable
      events.append(make_event(output, time_spine, state.ticks_per_beat))
            
   def element_sound(self, sound, time_spine, events, meta_events, state):
      tempo = sound.get("tempo")
      if tempo != None:
         tempo = float(tempo)
         value = int_range_check((60.0 / tempo) * 1000000, 0, MAX_24_BIT,
                                 "Tempo value", state.warnings)
         tempo_tag = Element("SetTempo", Value=str(value))
         meta_events.append(make_event(tempo_tag, time_spine, state.ticks_per_beat))
      dynamics = sound.get("dynamics")
      if dynamics != None:
         state.dynamics = int_range_check(dynamics, 0, MAX_7_BIT,
                                          "<sound dynamics='x'>", state.warnings)

   def element_key(self, key, time_spine, events, meta_events, state):
      fifths = key.findtext("fifths")
      if fifths != None:
         fifths = int_range_check(fifths, -7, 7, "<fifths>", state.warnings)
         mode = key.findtext("mode")
         if m2m_modes.has_key(mode):
            mode = m2m_modes[mode]
         else:
            mode = 0
         key_tag = Element("KeySignature", Fifths=str(fifths), Mode=str(mode))
         meta_events.append(make_event(key_tag, time_spine, state.ticks_per_beat))

   def element_time(self, time, time_spine, events, meta_events, state):
      numerator = int_range_check(time.findtext("./beats"), 0, MAX_7_BIT, "<time><beats>", state.warnings)
      beat_type = int_range_check(time.findtext("./beat-type"), 0, 256, "<time><beat-type>", state.warnings)
      denominator = int(log(beat_type) / log(2))
      clocks_per_tick = int(state.ticks_per_beat * 4 / beat_type)
      thirty_seconds = int((float(state.ticks_per_beat) * 8.0) / 24.0)
      time_sig = Element("TimeSignature",
                         Numerator = str(numerator),
                         LogDenominator = str(denominator),
                         MIDIClocksPerMetronomeClick = str(clocks_per_tick),
                         ThirtySecondsPer24Clocks = str(thirty_seconds))
      meta_events.append(make_event(time_sig, time_spine, state.ticks_per_beat))
         
__all__ = ["MusicXMLToMidiXML"]
