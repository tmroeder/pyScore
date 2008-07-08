"""
Code to convert from MusicXML to GUIDO
Python GUIDO tools

Copyright (c) 2002-2008 Michael Droettboom
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

# PLAN: Finish support for conversion from MusicXML to Guido

from pyScore.config import config
from pyScore import ElementTree
from pyScore.Guido.objects import core
from pyScore.Guido.objects.basic import all as basic
from pyScore.Guido.objects.advanced import all as advanced
from pyScore.Guido.tree_builder import GuidoTreeBuilder
from pyScore.MusicXML.conversion_constants import *
from pyScore.util.structures import *
from pyScore.util.rational import Rat

class MusicXMLToGuido:
   def __init__(self, tags):
      self._tags = tags
      self._warnings = config.get("warnings")
      self._verbose = config.get("verbose")

   ########################################
   # Utility methods

   def m2g_duration(self, duration, divisions):
      return Rat(1, 4) * Rat(1, divisions) * Rat(duration, 1)

   class State:
      def __init__(self):
         self.divisions = 144 # Is there a default divisions?
         self.first_sequence = True
         self.stem_direction = None
         self.notations = {}
         self.wedges = {}
         self.lyrics = None
         self.voice = 1
         self.time_spines = {}
         self.guido_durations = {}

   def dispatch_element(self, element, builder, state):
      """Given a MusicXML element <x>, dispatches a call to a method named element_x"""
      func_name = "element_%s" % element.tag.replace("-", "_")
      if hasattr(self, func_name):
         return getattr(self, func_name)(element, builder, state)
      return None

   ########################################
   # Toplevel methods

   def convert(self, tree):
      # TODO: deal with time-wise MusicXML scores (e.g. use Michael Good's XSLT transform first)
      assert ElementTree.iselement(tree)
      builder = GuidoTreeBuilder(self._tags)
      state = self.State()
      self.make_sequences(tree, builder, state)
      return builder.score

   def make_sequences(self, tree, builder, state):
      builder.begin_Segment()
      state.first_sequence = True
      for i, part in enumerate(tree.findall("./part")):
         self.make_sequence(part, i+1, tree, builder, state)
         state.first_sequence = False
      builder.end_Segment()

   def make_sequence(self, part, staff_number, tree, builder, state):
      voices_used = SortedListSet([1])
      for voice in part.findall("./measure/note/voice"):
         if not int(voice.text) in voices_used:
            voices_used.add(int(voice.text))
      state.first_voice = True
      for voice in voices_used.data:
         state.voice = voice
         state.lyrics = None
         builder.begin_Sequence()
         if len(voices_used.data) > 1:
            builder.add_Tag("staff", None, (staff_number,))
         self.make_metadata(tree, builder, state)
         first = False
         for measure in part.findall("./measure"):
            self.make_measure(measure, builder, state)
         builder.end_Sequence()
         state.first_voice = False
         state.first_sequence = False

   def make_metadata(self, tree, builder, state):
      if state.first_sequence:
         for title in tree.findall("./work/work-title"):
            builder.add_Tag("title", None, (title.text,))
         for creator in tree.findall("./identification/creator"):
            for type in supported_creators:
               if creator.get("type") == type:
                  builder.add_Tag(type, None, (creator.text,))

   def make_measure(self, measure, builder, state):
      # We sort each measure by absolute time so that things are in order
      # Also, we determine and set the Guido duration here so that we don't have
      # to deal with divisions tags later.
      time_spine = Rat(0, 1)
      last_duration = Rat(0, 1)
      elements = []
      for element in measure:
         if element.find("./chord") is None:
            time_spine += last_duration
         if element.tag == "attributes":
            state.divisions = int(element.findtext("./divisions") or state.divisions)
         state.time_spines[element] = time_spine
         # element.time_spine = time_spine
         state.guido_durations[element] = Rat(0, 1)
         # element.guido_duration = Rat(0, 1)
         duration = element.findtext("./duration")
         if element.tag == "backup":
            time_spine -= self.m2g_duration(int(duration), state.divisions)
         elif element.tag == "forward":
            time_spine += self.m2g_duration(int(duration), state.divisions)
         else:
            if duration != None:
               state.guido_durations[element] = self.m2g_duration(int(duration), state.divisions)
            elements.append(element)
         last_duration = state.guido_durations[element]

      time_spines = state.time_spines
      elements.sort(lambda x, y: cmp(time_spines[x], time_spines[y]))

      time_spine = Rat(0, 1)
      for element in elements:
         if state.time_spines[element] > time_spine:
            difference = state.time_spines[element] - time_spine
            builder.add_Empty(difference.num, difference.den)
            time_spine = state.time_spines[element]
         self.dispatch_element(element, builder, state)
         time_spine += state.guido_durations[element]
      builder.add_Barline()

   ########################################
   # generic conversion methods

   def begin_range(self, element_name, tag_name, element, builder, state):
      """Creates the Begin tag for things that have overlapping ranges.
      * element_name: the XPath to the MusicXML element in element
      * tag_name: the Guido tag name
      """
      for e in element.findall(element_name):
         if e.get("type") == "start":
            number = e.get("number", "1")
            builder.add_Tag(tag_name + "Begin", int(number), ())

   def end_range(self, element_name, tag_name, element, builder, state):
      """Creates the End tag for things that have overlapping ranges.
      * element_name: the XPath to the MusicXML element in element
      * tag_name: the Guido tag name
      """
      for e in element.findall(element_name):
         if e.get("type") == "stop":
            number = e.get("number", "1")
            builder.add_Tag(tag_name + "End", int(number), ())

   def begin_notation(self, category_elements, options, callback, builder, state):
      """Creates the Begin tag for non-overlapping notations
      * options: The elements that cause this behavior
      * callback: Given a MusicXML element, create a Guido Tag
      """
      for category_element in category_elements:
         for option in options:
            if not state.notations.has_key(option):
               element = category_element.find("./" + option)
               if element != None:
                  callback(option, builder)
                  state.notations[option] = None

   def end_notation(self, category_elements, options, callback, builder, state):
      """Creates the Begin tag for non-overlapping notations
      * options: The elements that cause this behavior
      * callback: Given a MusicXML element and builder, adds a Guido tag
      """
      if category_elements == []:
         for option in options:
            if state.notations.has_key(option):
               callback(option, builder)
               del state.notations[option]
      else:
         for option in options:
            if state.notations.has_key(option):
               remove = True
               for category_element in category_elements:
                  element = category_element.find("./" + option)
                  if element != None:
                     remove = False
                     break
               if remove:
                  callback(option, builder)
                  del state.notations[option]

   def single_notation(self, element, path, callback, builder, state):
      """Creates tags containing only one note.
      * path: Path from element to desired element
      * callback: Given the element and builder, adds the Guido tag"""
      element = element.find(path)
      if element != None:
         callback(element, builder)

   ########################################
   # Concrete elements

   def element_note(self, element, builder, state):
      chord = element.find("./chord") != None
      voice_tag = int(element.findtext("./voice") or "1")
      self.begin_range("./notations/slur", "slur", element, builder, state)
      self.begin_range("./notations/tied", "tie", element, builder, state)
      if state.voice == voice_tag:
         if not chord:
            self.begin_beam(element, builder, state)
            self.begin_notations(element, builder, state)
            self.begin_lyric(element, builder, state)
         duration = state.guido_durations[element]
         pitch_tag = element.find("./pitch")
         rest_tag = element.find("./rest")
         if pitch_tag != None:
            self.make_stems(element, builder, state)
            pitch_name = pitch_tag.findtext("./step").lower()
            octave = int(pitch_tag.findtext("./octave")) - 3
            accidental = m2g_accidental[int(pitch_tag.findtext("./alter") or "0")]
            if chord:
               note = builder.add_Event_to_Chord(pitch_name, octave, accidental,
                                                 duration.num, duration.den)
            else:
               note = builder.add_Event_not_in_Chord(pitch_name, octave, accidental,
                                                  duration.num, duration.den)
         elif rest_tag != None:
            note = builder.add_Event_not_in_Chord("_", num=duration.num, den=duration.den)
         if not chord:
            self.end_lyric(element, builder, state)
            self.end_notations(element, builder, state)
            self.end_beam(element, builder, state)
      self.end_range("./notations/tied", "tie", element, builder, state)
      self.end_range("./notations/slur", "slur", element, builder, state)

   def make_stems(self, element, builder, state):
      stem_direction = element.find("./stem")
      if stem_direction != None:
         if state.stem_direction != stem_direction.text:
            state.stem_direction = stem_direction.text
            builder.add_Tag("stems" + stem_direction.text.capitalize(), None, ())
      elif state.stem_direction != None:
         state.stem_direction = None
         builder.add_Tag("stemsAuto", None, ())

   def begin_beam(self, element, builder, state):
      for beam in element.findall("./beam"):
         if beam.text == "begin":
            number = beam.get("number", "1")
            if beam.get("repeater", "no") == "yes":
               tag = "tremolo"
            else:
               tag = "beam"
            builder.add_Tag(tag + "Begin", int(number), ())

   def end_beam(self, element, builder, state):
      for beam in element.findall("./beam"):
         if beam.text == "end":
            number = beam.get("number", "1")
            if beam.get("repeater", "no") == "yes":
               tag = "tremolo"
            else:
               tag = "beam"
            builder.add_Tag(tag + "End", int(number), ())

   def begin_notations(self, note, builder, state):
      dynamics = note.findall("./notations/dynamics")
      articulations = note.findall("./notations/articulations")
      self.end_notation(dynamics, acceptable_dynamic_names,
                        self.end_dynamic_callback, builder, state)
      self.end_notation(articulations, g2m_articulations,
                        self.end_articulation_callback, builder, state)
      self.begin_notation(articulations, g2m_articulations,
                          self.begin_articulation_callback, builder, state)
      self.begin_notation(dynamics, acceptable_dynamic_names,
                          self.begin_dynamic_callback, builder, state)
      self.single_notation(note, "./notations/technical/fingering", self.begin_fingering_callback, builder, state)
      self.single_notation(note, "./notations/fermata", self.begin_fermata_callback, builder, state)
      # TODO: MusicXML -> Guido ornament handling

   def end_notations(self, note, builder, state):
      self.single_notation(note, "./notations/fermata", self.end_fermata_callback, builder, state)
      self.single_notation(note, "./notations/technical/fingering", self.end_fingering_callback, builder, state)

   def begin_lyric(self, element, builder, state):
      lyric = element.find("./lyric")
      if lyric == None or lyric.get("number", "1") != "1":
         if state.lyrics != None:
            builder.add_Tag("lyricsEnd", None, (), use_parens=True)
            state.lyrics = None
      else:
         # NOTE: Only the first verse of lyrics in MusicXML can be stored in Guido
         if state.lyrics == None:
            state.lyrics = builder.add_Tag("lyricsBegin", None, ("",), use_parens=True)
         syllable = lyric.findtext("./text") or ""
         syllabic = lyric.findtext("./syllabic")
         space_before = True
         if lyric.find("./extend") != None:
            if not len(syllable):
               syllable = "_"
               space_before = False
         if syllabic in ("begin", "middle"):
            syllable += "-"
         if syllabic in ("middle", "end"):
            space_before = False
         if space_before and len(state.lyrics.text) and not state.lyrics.text.endswith(" "):
            state.lyrics.text += " "
         state.lyrics.text += syllable
         state.lyrics.args_list[0] = state.lyrics.text

   def end_lyric(self, element, builder, state):
      lyric = element.find("./lyric")
      if lyric != None:
         if lyric.find("./end-line") != None or lyric.find("./end-paragraph") != None:
            builder.add_Tag("lyricsEnd", None, (), use_parens=True)
            state.lyrics = None

   def begin_articulation_callback(self, articulation, builder):
      builder.add_Tag(articulation, None, (), mode="Begin", use_parens=True)

   def end_articulation_callback(self, articulation, builder):
      builder.add_Tag(articulation, None, (), mode="End", use_parens=True)

   def begin_dynamic_callback(self, dynamic, builder):
      builder.add_Tag("intens", None, (dynamic,), mode="Begin", use_parens=True)

   def end_dynamic_callback(self, dynamic, builder):
      builder.add_Tag("intens", None, (), mode="End", use_parens=True)

   def begin_fermata_callback(self, element, builder):
      builder.add_Tag("fermata", None, (), mode="Begin", use_parens=True)

   def end_fermata_callback(self, element, builder):
      builder.add_Tag("fermata", None, (), mode="End", use_parens=True)

   def begin_fingering_callback(self, element, builder):
      builder.add_Tag("fingering", None, (element.text,), mode="Begin", use_parens=True)

   def end_fingering_callback(self, element, builder):
      builder.add_Tag("fingering", None, (), mode="End", use_parens=True)

   def make_chord(self, note, builder, state):
      builder.add_to_Chord(note)

   def element_barline(self, element, builder, state):
      if state.first_voice:
         if element.findtext("./bar-style") == "light-light":
            builder.add_Tag("doubleBar", None, ())
         repeat = element.find("./repeat")
         ending = element.find("./ending")
         if ending != None:
            number = int(ending.get("number", "1"))
            type = ending.get("type", "start")
            if type == "start":
               builder.add_Tag("repeatEnd", None, (number,), mode="Begin", use_parens=True)
            elif type in ("stop", "discontinue"):
               builder.add_Tag("repeatEnd", None, (), mode="End", use_parens=True)
         elif repeat != None:
            direction = repeat.get("direction", "backward")
            times = int(repeat.get("times", "1"))
            if direction == "forward":
               if times > 1:
                  args = (times,)
               builder.add_Tag("repeatBegin", None, args)
            else:
               builder.add_Tag("repeatEnd", None, ())
         else:
            builder.add_Barline()

   def element_attributes(self, element, builder, state):
      if state.first_voice:
         for subelement in element:
            self.dispatch_element(subelement, builder, state)

   def element_key(self, element, builder, state):
      fifths = int(element.findtext("./fifths"))
      mode = element.findtext("./mode")
      key = str(fifths)
      if m2g_key.has_key(mode):
         if m2g_key[mode].has_key(fifths):
            key = m2g_key[mode][fifths]
      builder.add_Tag("key", None, (key,))

   def element_time(self, element, builder, state):
      # NOTE: There is no way to represent <senza-misura> and type="single-number" for meters in Guido
      symbol = element.get('symbol', 'normal')
      if m2g_time_symbol.has_key(symbol):
         time = m2g_time_symbol[symbol]
      else:
         time = "%s/%s" % (element.findtext("./beats"), element.findtext("./beat-type"))
      builder.add_Tag("meter", None, (time,))

   def element_clef(self, element, builder, state):
      sign = element.findtext("./sign")
      if not m2g_clef_type.has_key(sign):
         if self._warnings:
            print "WARNING: clef sign '%s' has no equivalent in Guido." % sign
      else:
         sign = m2g_clef_type[sign]
      line = element.findtext("./line")
      combined = sign + line
      if m2g_clef_name.has_key(combined):
         combined = m2g_clef_name[combined]
      octave_change = int(element.findtext("./clef-octave-change") or "0")
      if octave_change:
         if octave_change < 1:
            combined += "-"
         else:
            combined += "+"
         combined += str(int(abs(octave_change) * 7 + 1))
      builder.add_Tag("clef", None, (combined,))

   def element_direction(self, element, builder, state):
      for direction_type in element.findall("./direction-type"):
         for subelement in direction_type:
            self.dispatch_element(subelement, builder, state)

   def element_print(self, element, builder, state):
      if element.get("new-system", "no") == "yes":
         builder.add_Tag("newSystem", None, ())

   def element_dynamics(self, element, builder, state):
      for subelement in element:
         builder.add_Tag("intens", None, (subelement.tag,))

   def element_wedge(self, element, builder, state):
      type = element.get("type")
      number = int(element.get("number", "1"))
      if type in ("crescendo", "diminuendo"):
         builder.add_Tag(m2g_wedge[type] + "Begin", number, ())
         state.wedges[number] = m2g_wedge[type]
      elif type == "stop":
         builder.add_Tag(state.wedges[number] + "End", number, ())
         del state.wedges[number]

   def element_octave_shift(self, element, builder, state):
      size = int(element.get('size', '0'))
      direction = element.get('type', 'up')
      octave = m2g_octave_shift[direction] + str((abs(size) - 1) / 7)
      builder.add_Tag('oct', None, (octave,))

   def element_metronome(self, element, builder, state):
      # NOTE: Tempo names are not converted from MusicXML -> Guido, only metronome markings
      beat_unit = m2g_duration_type[element.findtext("./beat-unit")]
      per_minute = int(element.findtext("./per-minute"))
      dots = "." * len(element.findall("./beat-unit-dot"))
      builder.add_Tag("tempo", None, ("%d/%d%s=%d" % (beat_unit.num, beat_unit.den, dots, per_minute),))

   def element_words(self, element, builder, state):
      # NOTE: There is a limited vocabulary of written directions that get converted from MusicXML to Guido.  This conversion is not very smart or robust.

      # NOTE: Markings followed by dashes are not supported by MusicXML -> Guido
      text = element.text.replace(".", "")
      if m2g_words.has_key(text):
         builder.add_Tag(m2g_words[text], None, ())
