"""
Code to convert from MusicXML to GUIDO
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

# PLAN: Finish support for conversion from MusicXML to Guido

from pyScore.util.structures import *
from pyScore.Guido.objects import core
from pyScore.Guido.objects.basic import all as basic
from pyScore.Guido.objects.advanced import all as advanced
from pyScore.Guido.tree_builder import GuidoTreeBuilder
from pyScore.MusicXML.conversion_constants import *
from pyScore.util.rational import Rat

from pyScore.elementtree.ElementTree import iselement, tostring

class MusicXMLToGuido:
   def __init__(self, tags, warnings=True, verbose=False):
      self._tag_factory = core.TagFactoryClass(tags)
      self._warnings = warnings
      self._verbose = verbose

   def m2g_duration(self, duration, divisions):
      return Rat(1, 4) * Rat(1, divisions) * Rat(duration, 1)

   class State:
      def __init__(self):
         self.divisions = 144 # Is there a default divisions?
         self.stem_direction = None
         self.notations = {}
         self.wedges = {}

   def convert(self, tree):
      # TODO: deal with time-wise MusicXML scores (e.g. use Michael Good's XSLT transform first)
      assert iselement(tree)
      builder = GuidoTreeBuilder(self._tag_factory)
      state = self.State()
      self.make_sequences(tree, builder, state)
      return builder.score

   # generic conversion functions ########################################

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

   def dispatch_element(self, element, builder, state):
      """Given a MusicXML element <x>, dispatches a call to a method named element_x"""
      func_name = "element_%s" % element.tag.replace("-", "_")
      if hasattr(self, func_name):
         return getattr(self, func_name)(element, builder, state)
      return None

   # Concrete processing ########################################

   def make_sequences(self, tree, builder, state):
      builder.begin_Segment()
      first = True
      for part in tree.findall("./part"):
         self.make_sequence(part, tree, first, builder, state)
         first = False
      builder.end_Segment()

   def make_sequence(self, part, tree, first, builder, state):
      voices_used = SortedListSet([1])
      for voice in part.findall("./measure/note/voice"):
         if not int(voice.text) in voices_used:
            voices_used.add(int(voice.text))
      for voice in voices_used.data:
         builder.begin_Sequence()
         if first:
            self.make_metadata(tree, builder, state)
         first = False
         for measure in part.findall("./measure"):
            self.make_measure(measure, voice, builder, state)
         builder.end_Sequence()

   def make_metadata(self, tree, builder, state):
      for title in tree.findall("./work/work-title"):
         builder.add_Tag("title", None, (title.text,))
      for creator in tree.findall("./identification/creator"):
         for type in supported_creators:
            if creator.get("type") == type:
               builder.add_Tag(type, None, (creator.text,))

   def make_measure(self, measure, voice, builder, state):
      # We sort each measure by absolute time so that things are in order
      # Also, we determine and set the Guido duration here so that we don't have
      # to deal with divisions tags later.
      time_spine = Rat(0, 1)
      for element in measure:
         for divisions in element.findall(".//divisions"):
            state.divisions = int(divisions.text)
         element.time_spine = time_spine
         element.guido_duration = Rat(0, 1)
         duration = element.find("./duration")
         if element.tag == "backup":
            time_spine -= self.m2g_duration(int(duration.text), state.divisions)
         elif element.tag == "forward":
            time_spine += self.m2g_duration(int(duration.text), state.divisions)
         elif duration != None:
            element.guido_duration = self.m2g_duration(int(duration.text), state.divisions)
         if element.find("./chord") is None:
            time_spine += element.guido_duration
      
      # Filter notes and directions so we're only dealing with the current voice
      filtered = []
      for element in measure:
         if element.tag in ("note", "direction"):
            voice_tag = element.find("./voice")
            if voice_tag != None:
               if int(voice_tag.text) == voice:
                  filtered.append(element)
            else:
               if voice == 1:
                  filtered.append(element)
         elif not element.tag in ("forward", "backup"):
            filtered.append(element)
      filtered.sort(lambda x, y: cmp(x.time_spine, y.time_spine))

      time_spine = Rat(0, 1)
      for element in filtered:
         if element.time_spine > time_spine:
            difference = element.time_spine - time_spine
            builder.add_Empty(difference.num, difference.den)
            time_spine = element.time_spine
         self.dispatch_element(element, builder, state)
         time_spine += element.guido_duration
      builder.add_Barline()

   # element dispatch targets ########################################

   def element_note(self, element, builder, state):
      chord = element.find("./chord") != None
      self.make_stems(element, builder, state)
      if not chord:
         self.begin_beam(element, builder, state)
         self.begin_notations(element, builder, state)
      duration = element.guido_duration
      pitch_tag = element.find("./pitch")
      rest_tag = element.find("./rest")
      if pitch_tag != None:
         pitch_name = pitch_tag.findtext("./step").lower()
         octave = int(pitch_tag.findtext("./octave")) - 3
         accidental = m2g_accidental[int(pitch_tag.findtext("./alter"))]
         if chord:
            note = builder.add_Event_to_Chord(pitch_name, octave, accidental,
                                              duration.num, duration.den)
         else:
            note = builder.add_Event_not_in_Chord(pitch_name, octave, accidental,
                                                  duration.num, duration.den)
      elif rest_tag != None:
         note = builder.add_Event_not_in_Chord("_", num=duration.num, den=duration.den)

      if not chord:
         self.end_beam(element, builder, state)
         self.end_notations(element, builder, state)

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
      self.begin_range("./notations/slur", "slur", note, builder, state)
      self.begin_range("./notations/tied", "tie", note, builder, state)
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
      self.end_range("./notations/tied", "tie", note, builder, state)
      self.end_range("./notations/slur", "slur", note, builder, state)

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
      if element.findtext("./bar-style") == "light-light":
         builder.add_Tag("doubleBar", None, ())
      else:
         builder.add_Barline()

   def element_attributes(self, element, builder, state):
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
      # NOTE: There is no way to represent <senza-misura> and type="single-number"
      # in <time> tags in Guido
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
         builder.add_Tag(type + "Begin", number, ())
         state.wedges[number] = type
      elif type == "stop":
         builder.add_Tag(state.wedges[number] + "End", number, ())
         del state.wedges[number]

   def element_octave_shift(self, element, builder, state):
      size = int(element.get('size', '0'))
      direction = element.get('type', 'up')
      octave = m2g_octave_shift[direction] + str((abs(size) - 1) / 7)
      builder.add_Tag('oct', None, (octave,))
