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

class MusicXMLToMidiXML:
   def __init__(self, ticks_per_beat=TICKS_PER_BEAT):
      self._ticks_per_beat = ticks_per_beat
      self._warnings = config.get("warnings")
      self._verbose = config.get("verbose")

   class State:
      def __init__(self):
         self.divisions = DIVISIONS
         self.part_no = 0
         self.channel = 1

   def dispatch_element(self, element, time_spine, events, state):
      """Given a MusicXML element <x>, dispatches a call to a method named element_x"""
      func_name = "element_%s" % element.tag.replace("-", "_")
      if hasattr(self, func_name):
         return getattr(self, func_name)(element, time_spine, events, state)
      return None

   def convert_duration(self, duration, divisions):
      return int(float(duration) / float(divisions) * float(self._ticks_per_beat))
      
   def convert(self, music_xml):
      midi = Element("MIDIFile")
      SubElement(midi, "Format").text = "1"
      num_tracks = len(music_xml.findall("./part-list//score-part"))
      if num_tracks > 16:
         raise ValueError("Too many tracks to convert to MIDI (for now, at least).")
      SubElement(midi, "Tracks").text = str(num_tracks)
      SubElement(midi, "TicksPerBeat").text = str(self._ticks_per_beat)
      SubElement(midi, "TimestampType").text = "Absolute"
      
      state = self.State()
      self.make_tracks(music_xml, midi, state)
      return midi

   def make_tracks(self, music_xml, midi, state):
      # TODO: Make MIDI tempo track
      for i, (part, score_part) in enumerate(zip(music_xml.findall("./part"),
                                                 music_xml.findall("./part-list//score-part"))):
         state.part_no = i
         self.make_track(part, score_part, midi, state)

   def make_track(self, part, score_part, midi, state):
      time_spine = 0
      duration = 0
      events = []
      state.channel = state.part_no + 1
      for element in score_part:
         self.dispatch_element(element, time_spine, events, state)
      
      for measure in part:
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
               self.dispatch_element(element, time_spine, events, state)
                  
      events.sort(lambda x, y: cmp(x.time_spine, y.time_spine))
      track = SubElement(midi, "Track", number=str(state.part_no))
      for event in events:
         track.append(event)

   def make_event(self, time_spine, subevent):
      event = Element("Event")
      SubElement(event, "Absolute").text = str(time_spine)
      event.time_spine = time_spine
      event.append(subevent)
      return event

   def element_midi_instrument(self, midi_inst, time_spine, events, state):
      state.channel = int(midi_inst.findtext("./midi-channel") or state.channel)
      name = midi_inst.findtext("./midi-name")
      if name != None:
         program_name = Element("ProgramName")
         program_name.text = name
         events.append(self.make_event(time_spine, program_name))
      program = midi_inst.findtext("./midi-program")
      if program != None:
         program_change = Element("ProgramChange")
         SubElement(program_change, "Channel").text = str(state.channel)
         SubElement(program_change, "Number").text = program
         events.append(self.make_event(time_spine, program_change))

   def element_note(self, note, time_spine, events, state):
      if note.find("./rest") is None:
         duration = int(note.findtext("./duration") or "0")

         pitch = note.find("./pitch")
         pitch_name = pitch.findtext("./step")
         alter = int(pitch.findtext("./alter") or "0")
         octave = int(pitch.findtext("./octave") or "3")
         midi_number = pitch_names_to_semitones[pitch_name] + alter + (octave + 1) * 12

         note_on = Element("NoteOn")
         SubElement(note_on, "Channel").text = str(state.channel)
         SubElement(note_on, "Note").text = str(midi_number)
         SubElement(note_on, "Velocity").text = str(64)
         events.append(self.make_event(time_spine, note_on))
         
         note_off = Element("NoteOff")
         SubElement(note_off, "Channel").text = str(state.channel)
         SubElement(note_off, "Note").text = str(midi_number)
         SubElement(note_off, "Velocity").text = "0"
         events.append(self.make_event(
            time_spine + self.convert_duration(duration, state.divisions),
            note_off))
            
   def element_direction(self, direction, time_spine, events, state):
      for element in direction:
         self.dispatch_element(element, time_spine, events, state)

   def element_sound(self, sound, time_spine, events, state):
      if sound.get("tempo") != None:
         
