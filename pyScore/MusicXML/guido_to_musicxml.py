"""
Code to convert from pyGUIDO objects to MusicXML
Python GUIDO tools

Copyright (C) 2002 Michael Droettboom
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

from pyScore.elementtree.ElementTree import Element, SubElement, tostring

from pyScore.config import config
from pyScore.util.structures import *
from pyScore.Guido.objects import core
from pyScore.Guido.objects.basic.staff import staff as staff_tag
from pyScore.Guido.objects.basic.instrument import instrument as instrument_tag
from pyScore.MusicXML.conversion_constants import *
from pyScore.util.rational import Rat
from pyScore.util.config import *

import sys
from types import *

# NOTE: MusicXML doesn't seem to have a way to support Guido \\headsReverse
# NOTE: Guido \\noteFormat tag is completely unsupported
# NOTE: Guido \\splitChord tag is completely unsupported

config.add_option("", "--divisions", action="store", default=144, type="int")

class ExtendedSequence(core.INLINE_COLLECTION):
   """This class stores a few more bits of information about Guido sequences
that help with the re-ordering into MusicXML order."""
   def __init__(self, collection, number):
      self.collection = collection
      for item in self.collection:
         item.parent = self
      self.number = number
      self.staves = {}
      self.cross_staff = False
      self.voice = None

class GuidoToMusicXML:
   """This class handles conversion from a Guido object tree to a MusicXML
elementtree."""
   
   class State:
      """The state object stores state of various flags that can be changed in
the Guido stream, such as stem direction..."""
      def __init__(self):
         self.stem_direction = {}
         self.active_beams = DefaultDictionary(OverlappingRanges)
         self.active_slurs = OverlappingRanges()
         self.active_ties = OverlappingRanges()
         self.measure_no = 0
         self.last_tuplet = None
         self.last_ending = None

   def __init__(self):
      self._divisions = config.get("divisions")
      assert type(self._divisions) == IntType
      self._quarter_divisions = self._divisions * 4
      self._warnings = config.get("warnings")
      self._verbose = config.get("verbose")

   def g2m_duration(self, d):
      return int((d.num * self._quarter_divisions) / d.den)

   def convert(self, score):
      assert isinstance(score, core.Score)
      score.calc_time_spines()

      self.last_ending = None

      self.root = score_partwise = Element("score-partwise")
      SubElement(score_partwise, "work")
      SubElement(score_partwise, "identification")

      staff_layout, barlines = self.make_plan(score)
      self.make_part_list(score_partwise, staff_layout)
      self.make_parts(score_partwise, staff_layout, barlines)
      return score_partwise

   def make_plan(self, score):
      # NOTE: In GUIDO, barlines are "global": i.e. they affect all parts.  Therefore, we merge all barlines, but warn if there are barlines in subsequent parts that do not match those in the previous parts.

      # NOTE: Cross-staff beaming doesn't seem to convert from Guido to MusicXML
      
      # First we scan through all of the parts and sort by staff, and
      # keep track of where the barlines are

      # TODO: document GuidoToMusicXML.make_plan because it's really hairy
      barlines = SortedListSet()
      sequence_no = 1
      sequences = []
      found_staff_tag = False
      sequences = score.toplevel.collection
      for i, sequence in enumerate(sequences):
         sequence.number = i + 1
         sequence.staves = {}
         sequence.cross_staff = False
         sequence.voice = None

         barline_warnings = []
         if not found_staff_tag:
            current_staff = i + 1
         for item in sequence.collection:
            if isinstance(item, staff_tag):
               found_staff_tag = True
               current_staff = item.number
            else:
               sequence.staves[current_staff] = None
               item.staff = current_staff
               if isinstance(item, core.Barline):
                  if not item.time_spine in barlines:
                     barlines.add(item.time_spine)
                     if i and self._warnings:
                        barline_warnings.append(item.time_spine)
         if len(barline_warnings):
            sys.stderr.write(
               "WARNING: In part %d, barlines do not line up with previous parts at %s" %
               (i, ", ".join([str(x) for x in barline_warnings])))

      staff_layout = Grouper()
      staves_to_sequences = {}
      for i, sequence in enumerate(sequences):
         sequence_staves = sequence.staves.keys()
         for staff in sequence_staves:
            staves_to_sequences.setdefault(staff, []).append(sequence)
         staff_layout.join(sequence_staves[0])
         if len(sequence_staves) > 1:
            sequence.cross_staff = True
            for staff in sequence_staves[1:]:
               staff_layout.join(sequence_staves[0], staff)
      staff_layout = staff_layout.data
      for i, group in enumerate(staff_layout):
         for j, staff in enumerate(group):
            for sequence in sequences:
               for s in sequence.staves.keys():
                  sequence.staves[s] = s - i
            staff_layout[i][j] = staves_to_sequences[staff_layout[i][j]]
      for staff, seqs in staves_to_sequences.items():
         if len(seqs) > 1:
            for i, seq in enumerate(seqs):
               seq.voice = i + 1

      if self._verbose:
         print "Grouping sequences into parts:"
         print [[[x.number for x in y] for y in z] for z in staff_layout]
      return staff_layout, barlines.data
   
   def make_part_list(self, score_partwise, staff_layout):
      part_list = SubElement(score_partwise, "part-list")
      part_no = 1
      for i, group in enumerate(staff_layout):
         for part in group:
            score_part = SubElement(part_list, "score-part", id = "P" + str(part_no))
            # NOTE: Guido doesn't have named parts like MusicXML, so we grab it from the \\instrument tag
            SubElement(score_part, "part-name").text = "Music"
            part_no += 1

   def make_parts(self, score_partwise, staff_layout, barlines):
      # NOTE: Measures out-of-order (using arguments to the \\beam tag) in Guido are treated as in-order
      used_sequences = []
      part_no = 1
      for i, group in enumerate(staff_layout):
         for part in group:
            collection = []
            part_tag = SubElement(score_partwise, "part", id="P" + str(part_no))
            num_staves = 0
            first = True
            for sequence in part:
               if sequence not in used_sequences:
                  collection.extend(sequence.collection)
                  used_sequences.append(sequence)
                  num_staves = max(len(sequence.staves), num_staves)
            collection.sort(lambda x, y: cmp(x.time_spine, y.time_spine))
            state = self.State()
            measure = SubElement(part_tag, "measure", number=str(state.measure_no + 1))
            attributes = SubElement(measure, "attributes")
            SubElement(attributes, "divisions").text = str(DIVISIONS)
            if num_staves > 1:
               SubElement(attributes, "staves").text = str(num_staves)
            self.make_part(collection, barlines, part_tag, Rat(0, 1), measure, state)
            if state.last_ending != None:
               state.last_ending.set("type", "stop")
            # Delete empty measures (if any) at end of part
            if len(part_tag[-1]) == 0:
               part_tag.remove(part_tag[-1])
            part_no += 1

   def make_part(self, collection, barlines, part, time_spine, measure, state):
      last_item = None
      for item in collection:
         if isinstance(item, core.Empty):
            continue
         time_spine = self.adjust_time(time_spine, item.time_spine, measure)
         if isinstance(item, core.TAG):
            direction = SubElement(measure, "direction")
            self.dispatch_tag(item, measure, direction, state)
            if not len(direction):
               measure.remove(direction)
            else:
               if item.parent.voice != None:
                  SubElement(direction, "voice").text = str(item.parent.voice)
         if isinstance(item, (core.Barline, core.DURATIONAL)):
            if (state.measure_no < len(barlines) and
                item.time_spine >= barlines[state.measure_no]):
               state.measure_no += 1
               measure = SubElement(
                  part, "measure", number=str(state.measure_no + 1))
         if isinstance(item, core.EVENT):
            direction = None
            self.make_note(item, measure, state)
         if isinstance(item, core.Chord):
            direction = None
            self.make_chord(item, measure, state)
         time_spine += item.get_duration()
         last_item = item
      return time_spine, measure

   def adjust_time(self, current, next, measure):
      # We do g2m_duration on current and next so that the
      # subtraction is on integers, not rationals.
      if current != next:
         if next < current:
            backup = SubElement(measure, "backup")
            SubElement(backup, "duration").text = str(
               self.g2m_duration(current) -
               self.g2m_duration(next))
         else:
            forward = SubElement(measure, "forward")
            SubElement(forward, "duration").text = str(
               self.g2m_duration(next) -
               self.g2m_duration(current))
      return next

   # <note> elements ########################################

   def make_note(self, item, measure, state, chord=False):
      if item.get_duration() == 0:
         return
      note = SubElement(measure, "note")
      ties = []
      if len(item.get_tag("grace")):
         SubElement(note, "grace", slash="yes")
         self.make_full_note(item, note, state, chord)
         if not chord:
            ties = self.make_tie(item, note, state)
      elif len(item.get_tag("cue")):
         SubElement(note, "cue")
         self.make_full_note(item, note, state, chord)
         self.make_duration(item, note, state)
      else:
         self.make_full_note(item, note, state, chord)
         self.make_duration(item, note, state)
         if not chord:
            ties = self.make_tie(item, note, state)
      if item.parent.voice != None:
         SubElement(note, "voice").text = str(item.parent.voice)
      length, name = self.find_root_duration(item)
      if not length is None:
         SubElement(note, "type").text = name
      for i in range(item.dotting):
         SubElement(note, "dot")
      if isinstance(item, core.PITCHED):
         if g2m_accidental.has_key(item.accidental):
            SubElement(note, "accidental").text = g2m_accidental[item.accidental]
      self.make_time_modification(length, name, item, note, state)
      if state.stem_direction.has_key(item.parent.voice):
         SubElement(note, "stem").text = state.stem_direction[item.parent.voice]
      if item.parent.cross_staff:
         SubElement(note, "staff").text = str(item.staff)
      if not chord:
         self.make_tremolo_and_beam(item, note, state)
      notations = SubElement(note, "notations")
      if not chord:
         for tie in ties:
            notations.append(tie)
         self.make_tuplet(length, name, item, notations, state)
         self.make_slur(item, notations, state)
         for tag in g2m_articulations:
            if len(item.get_tag(tag)):
               articulations = SubElement(notations, "articulations")
               SubElement(articulations, tag)
         # EXT: Note-level dynamics do not seem to work in Turandot
         for intens in item.get_tag("intensity"):
            if intens.named in acceptable_dynamic_names:
               dynamics = SubElement(notations, "dynamics")
               SubElement(dynamics, intens.named)
         if len(item.get_tag("fermata")):
            SubElement(notations, "fermata")
         for fingering in item.get_tag("fingering"):
            technical = SubElement(notations, "technical")
            SubElement(technical, "fingering").text = fingering.text
      self.make_lyric(item, note, state)
      return note, notations

   def make_full_note(self, item, note, state, chord=False):
      if chord:
         SubElement(note, "chord")
      if isinstance(item, core.PITCHED):
         pitch = SubElement(note, "pitch")
         step = SubElement(pitch, "step")
         step.text = core.PITCHED.pitch_names_to_normal_pitch_names[item.pitch_name].upper()
         alter = SubElement(pitch, "alter")
         alter.text = str(core.PITCHED.accidentals_to_semitones[item.accidental])
         octave = SubElement(pitch, "octave")
         octave.text = str(item.octave + 3)
      else:
         SubElement(note, "rest")

   def make_duration(self, item, note, state):
      SubElement(note, "duration").text = str(self.g2m_duration(item.get_duration()))

   def make_tie(self, item, note, state):
      result = []
      for tie in item.get_tag("tie"):
         type = []
         if tie.is_first(item):
            type = ["start"]
            number = state.active_ties.begin(tie, "ties")
         elif tie.is_last(item):
            type = ["stop"]
            number = state.active_ties.end(tie)
         else:
            type = ["start", "stop"]
            number = state.active_ties.get_number(tie)
         for t in type:
            element = SubElement(note, "tie", type=t)
            result.append(Element("tied", type=t, number=str(number)))
      return result
               
   def find_root_duration(self, item):
      float_dur = float(item.num) / float(item.den)
      if float_dur > 2.0 or float_dur < 0.00390625: # 1/256
         if self._warnings:
            print "Duration '%s' is out of range for MusicXML" % float_dur
         return None, None
      dur = Rat(item.num, item.den)
      for (length, name) in g2m_duration_type:
         if dur <= length:
            return length, name
      item.raise_error("Error determining look of note.")

   def make_time_modification(self, length, name, item, note, state):
      if length != None and (length.num != item.num or length.den != item.den):
         dur = Rat(item.num, item.den)
         tuplet = length / dur
         time_modification = SubElement(note, "time-modification")
         SubElement(time_modification, "actual-notes").text = str(tuplet.num)
         SubElement(time_modification, "normal-notes").text = str(tuplet.den)

   def make_tremolo_and_beam(self, item, note, state):
      # EXT: tremolos don't seem to work in Turandot
      for tremolo in item.get_tag("tremolo"):
         type = "continue"
         if tremolo.is_first(item):
            type = "begin"
         elif tremolo.is_last(self):
            type = "end"
         SubElement(note, "beam", repeater='yes', number="1").text = type

      # EXT: secondary beaming doesn't seem to work in Turandot
      for beam in item.get_tag("beam"):

         if beam.is_first(item):
            number = state.active_beams[item.parent.voice].begin(beam, "beams")
            type = "begin"
         elif beam.is_last(item):
            number = state.active_beams[item.parent.voice].end(beam)
            type = "end"
         else:
            number = state.active_beams[item.parent.voice].get_number(beam)
            type = "continue"
         SubElement(note, "beam", number=str(number)).text = type

   def make_tuplet(self, length, name, item, notations, state):
      if length is None or (length.num == item.num and length.den == item.den):
         if state.last_tuplet != None:
            SubElement(state.last_tuplet, "tuplet", type="stop")
            state.last_tuplet = None
         return
      if state.last_tuplet == None:
         SubElement(notations, "tuplet", type="start")
      state.last_tuplet = notations

   def make_slur(self, item, notations, state):
      for slur in item.get_tag("slur"):
         type = None
         if slur.is_first(item):
            type = "start"
            number = state.active_slurs.begin(slur, "slurs")
         elif slur.is_last(item):
            type = "stop"
            number = state.active_slurs.end(slur)
         if type:
            SubElement(notations, "slur", type=type, number=str(number))

   def make_lyric(self, item, note, state):
      for lyric in item.get_tag("lyrics"):
         syllable, last = lyric.get_syllable(item)
         if syllable != "":
            l = SubElement(note, 'lyric', number="1")
            if syllable == "_":
               SubElement(l, "extend")
            else:
               if syllable.startswith("-"):
                  if syllable.endswith("-"):
                     SubElement(l, "syllabic").text = "middle"
                     syllable = syllable[1:-1]
                  else:
                     SubElement(l, "syllabic").text = "end"
                     syllable = syllable[1:]
               else:
                  if syllable.endswith("-"):
                     SubElement(l, "syllabic").text = "begin"
                     syllable = syllable[:-1]
                  else:
                     SubElement(l, "syllabic").text = "single"
               extend = False
               if syllable.endswith("_"):
                  extend = True
                  syllable = syllable[:-1]
               first = True
               # EXT: Elisions don't work correctly in Turandot.
               for part in syllable.split():
                  if not first:
                     SubElement(l, "elision")
                  SubElement(l, 'text').text = part
                  first = False
               if extend:
                  SubElement(l, "extend")
            if last:
               SubElement(l, "end-line")
         break

   def make_chord(self, chord, measure, state):
      if not self.make_ornaments(chord, measure, state):
         first = True
         for item in chord.collection:
            if isinstance(item, core.EVENT):
               note, notations = self.make_note(item, measure, state, chord=not first)
            first = False

   def make_ornaments(self, group, measure, state):
      # EXT: ornaments don't seem to work in Turandot
      found_one = False
      for ornament in g2m_ornaments.keys():
         ornaments = group.get_tag(ornament)
         if len(ornaments):
            if found_one:
               group.raise_error("You can not have nested ornaments.")
            found_one = True
            if not len(group.collection):
               group.raise_error("'%s' must have at least one note." % ornament)
            first_note = group.collection[0]
            if not isinstance(first_note, core.Note):
               group.raise_error(
                  "'%s' must have at least one note." +
                  "(Tags on these notes are not currently supported.)" %
                  ornament)
            note, notations = self.make_note(first_note, measure, state)
            ornaments_element = SubElement(notations, "ornaments")
            ornament_element = SubElement(ornaments_element, g2m_ornaments[ornament])
            if len(group.collection) > 1:
               second_note = group.collection[1]
               if not isinstance(second_note, core.Note):
                  group.raise_error("Second element in '%s' must be a note" % ornament)
               if second_note.accidental:
                  accidental_mark = SubElement(ornaments_element, "accidental-mark")
                  accidental_mark.text = str(core.PITCHED.accidentals_to_semitones[
                     second_note.accidental])
               # Get interval between two notes
               pitch1 = core.PITCHED.pitch_names_to_semitones[group.collection[0].pitch_name] % 12
               pitch2 = core.PITCHED.pitch_names_to_semitones[group.collection[1].pitch_name] % 12
               size = int(abs(pitch1 - pitch2))
               if g2m_ornament_size.has_key(size):
                  ornament_element.set("trill-sound", g2m_ornament_size[size])
               else:
                  ornament_element.set("trill-sound", "whole")
            else:
               ornament_element.set("trill-sound", "unison")
      return found_one

   # TAGS ########################################

   def dispatch_tag(self, tag_obj, measure, direction, state):
      func_name = "tag_%s%s" % (tag_obj.__class__.__name__, tag_obj.mode)
      if hasattr(self, func_name):
         return getattr(self, func_name)(tag_obj, measure, direction, state)
      if tag_obj.mode == "Begin":
         func_name = "tag_%s" % (tag_obj.__class__.__name__)
         if hasattr(self, func_name):
            return getattr(self, func_name)(tag_obj, measure, direction, state)
      return None

   # barline tags
   
   def tag_doubleBar(self, tag, measure, direction, state):
      if len(measure) > 1:
         barline = SubElement(measure, 'barline', location="left")
         SubElement(barline, "bar-style").text = "light-light"

   # beam_stem tags

   def tag_stemsAuto(self, tag, measure, direction, state):
      del state.stem_direction[tag.parent.voice]

   def tag_stemsUp(self, tag, measure, direction, state):
      state.stem_direction[tag.parent.voice] = "up"

   def tag_stemsDown(self, tag, measure, direction, state):
      state.stem_direction[tag.parent.voice] = "down"

   def tag_stemsUpEnd(self, tag, measure, direction, state):
      del state.stem_direction[tag.parent.voice]
   tag_stemsDownEnd = tag_stemsUpEnd

   # clef tags

   def tag_clef(self, tag, measure, direction, state):
      # EXT: Turandot doesn't seem to handle changing clefs mid-stream
      attributes = SubElement(measure, "attributes")
      clef = SubElement(attributes, "clef")
      if tag.parent.cross_staff:
         clef.set("number", str(tag.staff))
      if tag.type == 'gg':
         type = 'g'
         octave_bias = -1
      else:
         type = tag.type
         octave_bias = 0
      SubElement(clef, "sign").text = g2m_clef_type[type]
      SubElement(clef, "line").text = str(tag.clef_line)
      octave = int(tag.octave / 8) + octave_bias
      if octave != 0:
         SubElement(clef, "clef-octave-change").text = str(octave)

   # dynamics tags

   def tag_intensity(self, tag, measure, direction, state):
      if len(tag.events) == 0 and tag.named in acceptable_dynamic_names:
         direction_type = SubElement(direction, "direction-type")
         dynamics = SubElement(direction_type, "dynamics")
         SubElement(dynamics, tag.named)

   def tag_crescendo(self, tag, measure, direction, state):
      # TODO: support word-based (as opposed to wedge-based) *cresc.* and *dim.*
      pass
      
   def tag_crescendoBegin(self, tag, measure, direction, state):
      name = tag.__class__.__name__
      direction_type = SubElement(direction, "direction-type")
      SubElement(direction_type, "wedge", type=name)
   tag_diminuendoBegin = tag_crescendoBegin

   def tag_crescendoEnd(self, tag, measure, direction, state):
      direction_type = SubElement(direction, "direction-type")
      SubElement(direction_type, "wedge", type="stop")
   tag_diminuendoEnd = tag_crescendoEnd

   # fermata tags

   def tag_fermata(self, tag, measure, direction, state):
      if not len(tag.events):
         barline = SubElement(measure, 'barline')
         SubElement(barline, 'bar-style').text = 'none'
         SubElement(barline, 'fermata')
         
   # key tags

   def tag_key(self, tag, measure, direction, state):
      attributes = SubElement(measure, "attributes")
      key = SubElement(attributes, "key")
      SubElement(key, "fifths").text = str(tag.num_sharps_or_flats)
      SubElement(key, "mode").text = tag.key_mode

   # layout tags
   
   # EXT: System breaks don't work in Turandot.
   
   def tag_newSystem(self, tag, measure, direction, state):
      SubElement(measure, "print", {'new-system': 'yes'})

   # meter tags

   def tag_meter(self, tag, measure, direction, state):
      attributes = SubElement(measure, "attributes")
      if tag.named_meter != None:
         symbol = g2m_named_meter[tag.named_meter]
      else:
         symbol = 'normal'
      time = SubElement(attributes, "time", symbol=symbol)
      SubElement(time, "beats").text = str(tag.num)
      SubElement(time, "beat-type").text = str(tag.den)
      
   # repeat tags

   def tag_repeatBegin(self, tag, measure, direction, state):
      state.last_ending = None
      barline = SubElement(measure, "barline")
      SubElement(barline, "repeat", direction="forward",
                 times=str(tag.repeats))

   def tag_repeatEnd(self, tag, measure, direction, state):
      # EXT: multiple repeat endings do not seem to work in Turandot
      barline = SubElement(measure, "barline")
      if tag.mode == "Begin":
         if len(tag.events):
            if state.last_ending != None:
               state.last_ending.find("./ending").set("type", "stop")
               SubElement(state.last_ending, "repeat", direction="backward")
            state.last_ending = SubElement(barline, "ending", type="start",
                                           number=str(tag.repetition))
      else:
         SubElement(barline, "repeat", direction="backward")

   def tag_repeatEndEnd(self, tag, measure, direction, state):
      barline = SubElement(measure, "barline")
      state.last_ending = barline
      SubElement(barline, "ending", type="discontinue",
                 number=str(tag.repetition))

   # tempo tags

   def tag_tempo(self, tag, measure, direction, state):
      # EXT: tempo tags don't seem to work in Turandot
      length, name = self.find_root_duration(tag)
      direction_type = SubElement(direction, "direction-type")
      metronome = SubElement(direction_type, "metronome")
      SubElement(metronome, "beat-unit").text = name
      for dot in range(tag.dots):
         SubElement(metronome, "beat-unit-dot")
      SubElement(metronome, "per-minute").text = str(tag.bpm)
      if tag.tempo_name != None:
         direction_type = SubElement(direction, "direction-type")
         SubElement(direction_type, "words").text = tag.tempo_name
      sound = SubElement(direction, "sound",
                         tempo = str(int((tag.bpm * 4 * tag.num) / tag.den)))

   def tag_accelerando(self, tag, measure, direction, state):
      name = tag.name
      if len(name) > 5:
         good_name = name + "."
      else:
         good_name = name

      direction_type = SubElement(direction, "direction-type")
      SubElement(direction_type, "words").text = good_name
      if len(tag.events):
         direction_type = SubElement(direction, "direction-type")
         SubElement(direction_type, "dashes", type="start")
   tag_ritardando = tag_accelerando

   def tag_accelerandoEnd(self, tag, measure, direction, state):
      direction_type = SubElement(direction, "direction-type")
      SubElement(direction_type, "dashes", type="stop")
   tag_ritardandoEnd = tag_accelerandoEnd

   # text tags

   def tag_text(self, tag, measure, direction, state):
      direction_type = SubElement(direction, "direction-type")
      SubElement(direction_type, "words").text = tag.text

   def tag_title(self, tag, measure, direction, state):
      root = self.root
      work = root.find("work")
      SubElement(work, "work-title").text = tag.text

   def tag_composer(self, tag, measure, direction, state):
      root = self.root
      identification = root.find("identification")
      SubElement(identification, "creator", type="composer").text = tag.text

   def tag_lyricist(self, tag, measure, direction, state):
      root = self.root
      identification = root.find("identification")
      SubElement(identification, "creator", type="lyricist").text = tag.text

   def tag_mark(self, tag, measure, direction, state):
      direction_type = SubElement(direction, "direction-type")
      SubElement(direction_type, "rehearsal").text = tag.text

   def tag_label(self, tag, measure, direction, state):
      if not len(self.collection):
         direction_type = SubElement(direction, "direction-type")
         SubElement(direction_type, "words").text = tag.text

   # transpose tags

   def tag_octave(self, tag, measure, direction, state):
      # EXT: Octave shift does not seem to work with Turandot
      direction_type = SubElement(direction, "direction-type")
      SubElement(direction_type, "octave-shift",
                 type = g2m_octave_types[cmp(tag.octaves, 0)],
                 size = str(1 + 7 * abs(tag.octaves)))
      
   def tag_octaveEnd(self, tag, measure, direction, state):
      direction_type = SubElement(direction, "direction-type")
      SubElement(direction_type, "octave-shift",
                 type = "stop")
      
