"""
Helper class for building GUIDO trees
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

from pyScore.Guido.objects import core

from copy import copy
from inspect import isclass
import re
from types import *

_pitch_names = core.PITCHED.solfege_pitch_names + ["empty"]
_rer_pitch_name = ("(?P<pitch_name>%s|[a-g_])" %
                   "|".join([u"(?:%s)" % x for x in _pitch_names]))
_rer_octave1 = "(?P<octave1>[+\-]?[0-9]+)?"
_rer_accidental = "(?P<accidental>(?:is)|#+|&+)?"
_rer_octave2 = "(?P<octave2>[+\-]?[0-9]+)?"
_rer_num = "(?:\*(?P<num>[0-9]+))?"
_rer_den = "(?:/(?P<den>[0-9]+))?"
_rer_dotting = "(?P<dotting>\.*)"
_rer_duration = _rer_num + _rer_den + _rer_dotting
regex_event = re.compile(
    _rer_pitch_name +
    _rer_octave1 +
    _rer_accidental +
    _rer_octave2 +
    _rer_duration)

regex_tag_name = re.compile("[A-Za-z_][A-Za-z0-9_]*")
_arg_str = '(?P<arg>(?:(?P<key>[A-Za-z_][A-Za-z0-9_]*)=)?(?:")?(?P<value>[^"]*)(?:")?)'
regex_arg = re.compile(_arg_str)
regex_tag = re.compile(
    r'\\(?P<name>[A-Za-z_][A-Za-z0-9_]*)(:(?P<id>[0-9]+))?(?:\<(?P<args>[^>]*)\>)?'
    )

default_note = {'pitch_name': 'c',
                'octave': 1,
                'accidental': '',
                'num': 1,
                'den': 4,
                'dotting': ''}

class GuidoTreeBuilder:
   # high-level interface

   def __init__(self, tags):
      self.score = self.current_collection = core.Score()
      self._stack = [self.current_collection]
      self._active_tags = []
      self._last_event = self.get_Event(**default_note)
      self._last_octave = default_note['octave']
      self.unknown_tags = {}
      if type(tags) not in (ListType, TupleType):
         tags = [tags]
      self._registered_tags = {}
      for t in tags:
         self.register_module_of_tags(t)
        
   def register_module_of_tags(self, t):
      if not type(t) == DictType:
         t = t.__dict__
      for key, val in t.items():
         if (isclass(val) and
             issubclass(val, core.TAG)):
            self._registered_tags[key] = val

   def begin_Segment(self, pos=None):
      self.set_as_collection(core.Segment(pos=pos))

   def end_Segment(self, pos=None):
      self.reset_collection(core.Segment)

   def begin_Sequence(self, pos=None):
      self._last_event = self.get_Event(**default_note)
      self._last_octave = default_note['octave']
      self.set_as_collection(core.Sequence(pos=pos))

   def end_Sequence(self, pos=None):
      # We do as best we can to make sure tags are closed
      if isinstance(self.current_collection, core.Chord):
         self.reset_collection()
      for i in range(len(self._active_tags) - 1, -1, -1):
         tag = self._active_tags[i]
         new_tag = copy(tag)
         new_tag.mode = "End"
         new_tag.events = []
         new_tag.args_list = []
         new_tag.args_dict = {}
         self.add(new_tag)
      self.reset_collection(core.Sequence)

   def add_Event(self, *args, **kwargs):
      note = self.get_Event(*args, **kwargs)
      self.add(note)
      self._last_event = note
      return note

   def add_Tag(self, *args, **kwargs):
      tag_obj = self.get_Tag(*args, **kwargs)
      if tag_obj.mode == "Begin":
         self.add(tag_obj)
         self.add_active_tag(tag_obj)
      elif tag_obj.mode == "End":
         self.remove_active_tag(tag_obj)
         self.add(tag_obj)
      else:
         self.add(tag_obj)
      return tag_obj

   def add_Empty(self, num=1, den=4):
      empty = self.get_Event("empty", num=num, den=den)
      self.add(empty)

   def add_Event_to_Chord(self, *args, **kwargs):
      note = self.get_Event(*args, **kwargs)
      if not isinstance(self.current_collection, core.Chord):
         chord = core.Chord()
         self.current_collection.collection[
            self.current_collection.collection.index(self._last_event)] = chord
         chord.collection.append(self._last_event)
         self._stack.append(self.current_collection)
         self.current_collection = chord
      self.add(note)
      self._last_event = note

   def add_Event_not_in_Chord(self, *args, **kwargs):
      note = self.get_Event(*args, **kwargs)
      if isinstance(self.current_collection, core.Chord):
         self.reset_collection()
      self.add(note)
      self._last_event = note

   def begin_Chord(self, pos=None):
      self.set_as_collection(core.Chord(pos=pos))

   def end_Chord(self):
      self.reset_collection(core.Chord)

   def add_Barline(self, pos=None):
      if isinstance(self.current_collection, core.Chord):
         self.reset_collection()
      self.add(core.Barline(pos=pos))

   # low-level interface
      
   def add(self, obj):
      """Adds an object to the current part."""
      self.current_collection.append(obj)
      for tag in self._active_tags:
         obj.tags.setdefault(tag.__class__.__name__, []).append(tag)
         if not isinstance(self.current_collection, core.Chord):
            tag.events.append(obj)

   def set_as_collection(self, collection, add=True):
      """Makes the collection the current one"""
      if add:
         self.add(collection)
      self._stack.append(collection)
      self.current_collection = collection

   def reset_collection(self, assert_type=None):
      """Pops the collection up a level"""
      top = self._stack.pop()
      if assert_type:
         assert type(top) == assert_type
      self.current_collection = self._stack[-1]

   def add_active_tag(self, tag_obj):
      assert isinstance(tag_obj, core.TAG)
      self._active_tags.append(tag_obj)
      
   def remove_active_tag(self, tag_obj):
      assert isinstance(tag_obj, core.TAG)
      active_tags = self._active_tags
      for i in range(len(active_tags) - 1, -1, -1):
         if (active_tags[i].name == tag_obj.name and
             active_tags[i].id == tag_obj.id):
            assert active_tags[i].mode == "Begin"
            del active_tags[i]
            return
      tag_obj.raise_error(
         "'\\%sEnd' appears before '\\%sBegin'" %
         (tag_obj.name, tag_obj.name))

   # Factories

   def get_Event(self, pitch_name=None, octave=None, accidental=None,
                 num=None, den=None, dotting=None, octave2=None, pos=None):
      def fill_in(num, den, dotting):
         if num is None:
            if den is None:
               num = self._last_event.num
               den = self._last_event.den
               if dotting == "":
                  dotting = self._last_event.dotting
            else:
               num = 1
         else:
            if den is None:
               den = 1
         num = int(num)
         den = int(den)
         if type(dotting) in (StringType, UnicodeType):
            dotting = len(dotting)
         return num, den, dotting

      if octave is None:
         octave = octave2
      if pitch_name == "_":
         num, den, dotting = fill_in(num, den, dotting)
         return core.Rest(num, den, dotting, pos=pos)
      if pitch_name == "empty":
         num, den, dotting = fill_in(num, den, dotting)
         return core.Empty(num, den, dotting, pos=pos)
      if pitch_name in core.PITCHED.pitch_names:
         if octave is None:
            octave = self._last_octave
         octave = int(octave)
         self._last_octave = octave
         num, den, dotting = fill_in(num, den, dotting)
         return core.Note(pitch_name, octave, accidental,
                          num, den, dotting, pos=pos)
      match = regex_event.match(pitch_name)
      if match != None:
         matches = match.groupdict()
         return self.get_Event(matches['pitch_name'], matches['octave1'],
                               matches['accidental'], matches['num'],
                               matches['den'], matches['dotting'],
                               matches['octave2'], pos=pos)
      else:
         raise ValueError("'%s' is not a valid GUIDO pitch name, note or rest." %
                          pitch_name)

   def get_Tag(self, name, id, args, pos=None, mode="", use_parens=False):
      if (not type(name) in (StringType, UnicodeType) or len(name) < 1 or
          regex_tag_name.match(name) is None):
         raise ValueError("'%s' is an invalid tag name." % str(name))

      if name.startswith('\\'):
         match = regex_tag.match(name)
         if not match is None:
            matches = match.groupdict()
            return self.__call__(
               matches['name'], matches['id'], matches['args'],
               pos=pos)
         else:
            raise ValueError("'%s' is not a valid tag." % name)
            
      if id != None:
         try:
            id = int(id)
         except ValueError:
            raise ValueError("'%s' is an invalid tag id number." % id)

      args_list = []
      args_dict = {}
      if type(args) in (TupleType, ListType):
         args_list = args
      elif type(args) == type({}):
         args_dict = args
      elif type(args) in (StringType, UnicodeType):
         first = True
         while len(args):
            if not first:
               if args.startswith(","):
                  args = args[1:].strip()
               else:
                  raise ValueError("Couldn't parse arguments to tag '%s'" % name)
            first = False
            match = regex_arg.match(args)
            if match == None:
               raise ValueError("'%s' is an invalid argument to tag '%s'." %
                                (arg, name))
            match_dict = match.groupdict()
            if match_dict['key'] != None:
               args_dict[match_dict['key']] = match_dict['value']
            else:
               args_list.append(match_dict['value'])
            args = args[match.end("arg"):].strip()

      if self._registered_tags.has_key(name):
         tag_cls = self._registered_tags[name]
      else:
         if name.endswith("Begin"):
            name = name[:-5]
            mode = "Begin"
         elif name.endswith("End"):
            name = name[:-3]
            mode = "End"
         if self._registered_tags.has_key(name):
            tag_cls = self._registered_tags[name]
         else:
            tag_cls = self._registered_tags['DEFAULT_TAG']
            self.unknown_tags[tag['name']] = None
      tag = tag_cls(name, id, args_list, args_dict, pos=pos)
      tag.mode = mode
      tag.use_parens = use_parens
      return tag
