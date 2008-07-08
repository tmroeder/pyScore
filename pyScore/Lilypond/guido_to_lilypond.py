"""
Code to convert from pyGUIDO objects to LilyPond
Python GUIDO tools

Copyright (C) 2002-2008 Michael Droettboom
Copyright (C) 2006 Stephen Sinclair
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
from pyScore.util.structures import *
from pyScore.Guido.objects import core
#from pyScore.Guido.objects.basic.staff import staff as staff_tag
#from pyScore.Guido.objects.basic.instrument import instrument as instrument_tag
from pyScore.Guido.objects.basic import text
from pyScore.util.config import *
from pyScore.util.Rat import rat

import sys
from math import log

from lilypond import *

class GuidoToLilypond:
   """This class handles conversion from a Guido object tree to a Lilypond score"""

   class State:
      """The state object stores state of various flags that can be changed in
the Guido stream, such as stem direction..."""
      def __init__(self):

         # This value will be used to modify the octave of following notes
         # during the presence of octavation
         self.octavation = 0

         # These attributes will be transfered to the next note that
         # appears, and then cleared.
         self.next_note_attributes = LilypondNoteAttributes.copy()

         self.previous_note = None

   def __init__(self):
      self._warnings = config.get("warnings")
      self._verbose = config.get("verbose")
      self.state = self.State()

   def convert(self, score):
      assert isinstance(score, core.Score)
      score.calc_time_spines()

      self.last_ending = None

      ly_metadata = None
      guido_metadata = self.find_guido_metadata(score.toplevel)
      if guido_metadata!=None and len(guido_metadata)>0:
         ly_metadata = LilypondElement('header', [])
         for element in guido_metadata:
            # 'lyricist' becomes 'poet' - other metadata tags have the same name in Ly and Gmn
            if isinstance(element, text.lyricist):
               ly_metadata.contents.append(LilypondTag('poet', ''.join(element.args_list)))
            else:
               ly_metadata.contents.append(LilypondTag(element.name, ''.join(element.args_list)))

      ly_score = LilypondElement('score',[])

#      self.dump_guido_element(score)
      element = self.convert_guido_element(score.toplevel)
      if element: ly_score.contents.append(element)

      ly_tree = [LilypondElement('version', '"2.6.3"')]
      if ly_metadata: ly_tree.append(ly_metadata)
      if ly_score:    ly_tree.append(ly_score)

      return ly_tree

   # Parse any Guido element into an equivalent Lilypond element
   # If a collection is encountered, function calls itself for
   # each element in the collection.
   def convert_guido_element(self, guido_element):
      if isinstance(guido_element, core.Note) or isinstance(guido_element, core.Rest):
         return self.convert_guido_note(guido_element)

      elif isinstance(guido_element, core.COLLECTION):
         collection = self.convert_guido_element_list(guido_element.collection)

         # Clear forwarded attributes if collection has ended
         # because tags should not affect tags in parent collection.
         # TODO: clear more state variables here??
         self.state.next_note_attributes = LilypondNoteAttributes.copy()

         # Check for Staff tags
         # Note: staff changes during a sequence will be ignored
         staff = None
         for i in collection:
            if isinstance(i, LilypondTag) and i.name=='Staff':
               collection.remove(i)
               if not staff:
                  staff = i

         if isinstance(guido_element, core.Segment):
            return LilypondParallel(None,collection)
         elif isinstance(guido_element, core.Chord):
            chord = LilypondChord(collection)

            # Commute all note attributes out to chord element
            # Length of chord is longest contained note length
            chord.duration = rat(0)
            for i in chord.contents:
               if isinstance(i, LilypondNote):
                  if i.duration > chord.duration:
                     chord.duration = i.duration
                  for a in i.attributes:
                     if i.attributes[a]:
                        chord.attributes[a] = i.attributes[a]
                        i.attributes[a] = None

            return chord

         else: # simple collection
            if staff:
               return LilypondElement('context', (staff, LilypondElement(None, collection)))
            else:
               return LilypondElement(None,collection)

      elif isinstance(guido_element, core.TAG):
         return self.convert_guido_tag(guido_element)

      elif isinstance(guido_element, core.Barline):
         return LilypondBarline()

      return None

   def convert_guido_element_list(self, guido_element_list):
      collection = []
      tuplet = []
      tag_depth = 0
      for i in guido_element_list:
         # Check for 'Begin' tags
         # Since enclosing tags are in-line with notes they
         # contain, we have to create subsequences for them.
         # If one is encountered, collect them until a matching 'End'
         # tag is found. We assume that nested tags don't overlap.
         # There is a special case for "repeatBegin" and "repeatEnd" pairs.
         if isinstance(i, core.TAG):
            if i.mode=='Begin' or i.name=='repeatBegin':
               tag_depth += 1
               if tag_depth==1:
                  tag_collection = []
                  tag = i
                  continue
            elif i.mode=='End' or (i.name=='repeatEnd' and len(i.args_list)==0):
               tag_depth -= 1
               if tag_depth < 0:
                  raise 'Tag depth error!'
               elif tag_depth == 0:
                  tmp = self.convert_guido_tag_collection(tag_collection, tag)
                  if tmp:
                     collection.append(tmp)
                  continue

         if tag_depth > 0:
            tag_collection.append(i)
         else:
            ly_element = self.convert_guido_element(i)
            if ly_element:
               if isinstance(ly_element, LilypondNote):
                  # For notes, check if they are part of a tuplet.
                  # If so, collect them separately,
                  # otherwise add them to the collection
                  if self.part_of_tuplet(ly_element):
                     tuplet = self.handle_tuplet(ly_element, tuplet, collection)
                  else:
                     collection.append(ly_element)
               else:
                  collection.append(ly_element)

      # Some Begin tag was not match with an End
      if tag_depth > 0:

         # This is okay for repeatBegin tags that have multiple repeatEnds
         # So search for them and convert accordingly
         if tag.name=='repeatBegin':
            tmp = self.convert_guido_repeat_alternatives(tag_collection, tag)
            if tmp:
               collection += tmp

      return collection

   # This function is for tags that have Begin and End modes
   def convert_guido_tag_collection(self, tag_collection, tag):
      collection = self.convert_guido_element_list(tag_collection)

      if tag.name=='tie':                     return LilypondTie(collection)
      if tag.name in ['slur','sl']:           return LilypondSlur(collection)
      if tag.name in ['beam','bm']:           return LilypondBeam(collection)
      if tag.name in ['trill','tr']:          return LilypondTrill(collection)
      if tag.name in ['staccato','stacc']:    return LilypondStaccato(collection)
      if tag.name in ['tenuto','ten']:        return LilypondTenuto(collection)
      if tag.name in ['accent']:              return LilypondAccent(collection)
      if tag.name in ['fermata']:             return LilypondFermata(collection)
      if tag.name in ['trill']:               return LilypondTrill(collection)
      if tag.name in ['mordent']:             return LilypondMordent(collection)
      if tag.name in ['turn']:                return LilypondTurn(collection)
      if tag.name in ['prall']:               return LilypondPrall(collection)  # note: part of guido??
      if tag.name in ['tremolo','trem']:      return LilypondTremolo(collection)

      if tag.name=='accel':                   return LilypondTextSpanner('accel.', collection)
      if tag.name=='rit':                     return LilypondTextSpanner('ritard.', collection)
      if tag.name=='cresc':                   return LilypondCrescendo(collection)
      if tag.name=='dim':                     return LilypondDiminuendo(collection)
      if tag.name=='grace':                   return LilypondElement('grace', collection)

      if tag.name in ['intens','i']:
         arg = tag.args_list[0]
         if arg in ['ppp','pp','p','mp','mf','f','ff','fff','fff','fp','sf',
                    'sff','sp','spp','sfz','rfz']:
            return LilypondDynamic(arg, collection)

      if tag.name=='repeatBegin':
         args = ''.join(tag.args_list)     #  = repeat count
         if not args:
            args = '2'
         return LilypondElement('repeat', ('volta', args, LilypondElement(None, collection)))

      if tag.name=='repeatEnd':               return LilypondElement(None, collection)

      # TODO: Cue notes are somewhat complex to do in Lilypond. For
      #       now, it is better to not keep them in the score at all.
      if tag.name=='cue':   return None;

      return LilypondGroup(collection)

   def handle_tuplet(self, element, tuplet, collection):
      tuplet.append(element)
      if not self.part_of_tuplet(tuplet):
         # calculate the most frequency duration in the tuplet
         dur = []
         count = []
         for i in tuplet:
            if i.duration in dur:
               count[dur.index(i.duration)] += 1
            else:
               dur.append(i.duration)
               count.append(1)
         freq_dur = dur[count.index(max(count))].den

         # look up which ratio it represents
         # TODO: better and more general way to do this
         #       for example, how to handle 4:7?
         if   (freq_dur==3):      ratio = rat(2,3)
         elif (freq_dur==5):      ratio = rat(4,5)
         elif (freq_dur==7):      ratio = rat(8,7)
         # For now, let it raise an exception if ratio is not defined

         for note in tuplet:
            note.duration = note.duration/ratio
         collection.append(
            LilypondElement('times',
                            ('%d/%d'%((ratio.num,ratio.den)),
                             LilypondElement(None, tuplet))))
         tuplet = []
      return tuplet

   def convert_guido_note(self, guido_note):
      if isinstance(guido_note, core.Rest):
         notename = 'r'
      else:
         accidental = ''
         for i in guido_note._get_accidental():
            accidental += {'&': 'es', '#': 'is', 'e': 'e', 'i': 'i', 's': 's'}[i]
         i = int(guido_note._get_octave()) #+self.state.octavation (TODO)
         octave = ''
         if i>0:
            octave = "'"*i
         elif i<0:
            octave = ","*(-i)
         notename = str(guido_note._get_pitch_name())
         if notename in guido_note.pitch_names_to_normal_pitch_names:
            notename = guido_note.pitch_names_to_normal_pitch_names[notename]
         notename += accidental+octave

      # Create a note structure
      note = LilypondNote(notename, rat(guido_note._num, guido_note._den),
                          guido_note._dotting)

      # Copy any attribute values forwarded from previous Guido tags
      for i in self.state.next_note_attributes:
         if self.state.next_note_attributes[i]:
            note.attributes[i] = self.state.next_note_attributes[i]
            self.state.next_note_attributes[i] = None

      # Remember one previous note
      self.state.previous_note = note

      return note

   def convert_guido_tag(self, guido_tag):
#      print 'Tag',guido_tag.name, guido_tag.id, guido_tag.mode, guido_tag.args_list
      if guido_tag.name=='oct':
         # octave transposition
         transpose = int(guido_tag.args_list[0])
         self.state.octavation = transpose
         return LilypondScheme('set-octavation', transpose)

      elif guido_tag.name=='clef':
         clef = ''.join(guido_tag.args_list)
         translate_clef = {'treble':'treble', 'bass':'bass', 'alto':'alto', 'basso':'bass',
                           'violino':'violin', 'f':'treble', 'g':'bass',
                           'c':'alto', 'perc':'percussion'} #, 'gg':None, 'f3':None}
         if clef in translate_clef:
            return LilypondElement('clef', translate_clef[clef])
         return None

      # TODO: this function needs to be tested harshly!
      #       only an approximation based on key.gmn
      # Note: testing indicates that it doesn't
      #       work perfectly.
      elif guido_tag.name=='key':
         key = ''.join(guido_tag.args_list)
         majorminor = None
         if len(key)>0 and key[0] in 'abcdefgh':
            majorminor = 'minor'
         elif len(key)>0 and key[0] in 'ABCDEFGH':
            majorminor = 'major'

         if majorminor:
            if len(key)>1:
               key = key[0] + {'&': 'es', '#': 'is', 'e': 'e', 'i': 'i', 's': 's'}[key[1:]]
         else:
            key = -int(key)
            keymap = ['c','des','d','ees','e','f','ges','g','aes','a','bes','b']
            if key<0:
               key += len(keymap)+1
               majorminor = 'minor'
            else:
               majorminor = 'major'
            key = keymap[key]
         return LilypondElement('key', (key.lower(), LilypondElement(majorminor)))

      elif guido_tag.name=='tempo':
         if len(guido_tag.args_list)>0:
            tempo = guido_tag.args_list[0]
            self.state.next_note_attributes['text'] = '^"%s"'%tempo

      elif guido_tag.name=='staff':
         # Note: Staff tags will get commuted to beginning of sequence
         return LilypondTag('Staff', ''.join(guido_tag.args_list))

      elif guido_tag.name=='meter':
         meter = ''.join(guido_tag.args_list)
         if meter in ['c','C']:   meter = '4/4'
         if meter in ['c/','C/']: meter = '2/4'
         return LilypondElement('time', meter)

      elif guido_tag.name=='stemsUp':
         return LilypondElement('stemUp')

      elif guido_tag.name=='stemsDown':
         return LilypondElement('stemDown')

      elif guido_tag.name=='stemsAuto':
         return LilypondElement('stemNeutral')

      elif guido_tag.name=='bar':
         return LilypondBarline()
      elif guido_tag.name=='doubleBar':
         return LilypondElement(None, '||')
      elif guido_tag.name=='tactus':
         return LilypondElement(None, '.|')

      if guido_tag.name in ['intens','i']:
         arg = guido_tag.args_list[0]
         if arg in ['ppp','pp','p','mp','mf','f','ff','fff','fff','fp','sf',
                    'sff','sp','spp','sfz','rfz']:
            self.state.next_note_attributes['dynamics'] = '\\'+arg

   def part_of_tuplet(self, note):
      # "note" can be a single note or a list of notes
      # If the total duration (times 32) is not a power of
      # two or =1, we assume it is part of a tuple.
      dur = 0
      if (isinstance(note,list)):
         for i in note:
            dur += (i.duration)
      else:
         dur = note.duration

      if dur==0:
         return False
      log2 = log(dur*32, 2)
      return not ((log2==int(log2)) or float(dur)==1)

   def dump_guido_element(self, element, indent=''):
      print indent+element.__class__.__name__,
      if isinstance(element, core.TAG):
         print element.mode, element.id, ''.join(element.args_list),
         print
      elif isinstance(element, core.Note):
         print element
      else:
         print
      if isinstance(element, core.COLLECTION):
         for i in element.collection:
            self.dump_guido_element(i, indent+'  ')

   # Find metadata tags scattered throughout the GUIDO file.
   # (They should actually all be in the beginning of the first sequence.)
   # In Lilypond, they are collected into the \header{} tag.
   def find_guido_metadata(self, element):
      if isinstance(element, text.title):
         return element
      elif isinstance(element, text.composer):
         return element
      elif isinstance(element, text.lyricist):
         return element
      elif isinstance(element, core.COLLECTION):
         metadata = []
         for i in element.collection:
            m = self.find_guido_metadata(i)
            if isinstance(m, list):
               for j in m:
                  metadata.append(j)
            elif m!=None:
               metadata.append(m)
         return metadata

   # Convert a tag collection for repeats with multiple alternative endings
   # Note: Since in GUIDO the alternatives are numbered (and can therefore
   #       be out of order), we sort them by their number before adding
   #       them to the Lilypond element list.
   def convert_guido_repeat_alternatives(self, tag_collection, tag):
      if (tag.name != 'repeatBegin'):
         return []

      repeat = None
      alternatives = []
      collection = []
      n = 0
      for i in tag_collection:
         if isinstance(i, core.TAG) and i.name=='repeatEnd':
            if repeat is None:
               repeat = LilypondElement('repeat', ('volta', '2', LilypondElement(None, collection)))

            if i.mode=='Begin':
               # try to convert the alternative number to an integer
               try:
                  num = int(''.join(i.args_list))
               except:
                  num = 0

               # keep only the first element of the converted list
               # (i.e., what is between repeatEnd<Begin> and repeatEnd<End>)
               alternatives.append([num, self.convert_guido_element_list(tag_collection[n:])[0]])
            collection = []
         else:
            collection.append(self.convert_guido_element(i))
         n += 1

      # Sort alternatives by index number and keep only the element list
      alternatives.sort()
      collection = []
      for i in alternatives:
         collection.append(i[1])

      return [repeat, LilypondElement('alternative', collection)]
