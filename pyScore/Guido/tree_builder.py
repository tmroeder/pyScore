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

class GuidoTreeBuilder:
   # high-level interface

   def __init__(self, tag_factory=core.TagFactory):
      self.score = self.current_collection = core.Score()
      self._stack = [self.current_collection]
      self._active_tags = []
      self._tag_factory = tag_factory
      self._last_event = None

   def begin_Segment(self, pos=None):
      self.set_as_collection(core.Segment(pos=pos))

   def end_Segment(self, pos=None):
      self.reset_collection(core.Segment)

   def begin_Sequence(self, pos=None):
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
         self.add(new_tag)
      self.reset_collection(core.Sequence)

   def add_Event(self, *args, **kwargs):
      note = core.EventFactory(*args, **kwargs)
      self.add(note)
      self._last_event = note
      return note

   def add_Tag(self, *args, **kwargs):
      tag_obj = self._tag_factory(*args, **kwargs)
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
      empty = core.EventFactory("empty", num=num, den=den)
      self.add(empty)

   def add_Event_to_Chord(self, *args, **kwargs):
      note = core.EventFactory(*args, **kwargs)
      if not isinstance(self.current_collection, core.Chord):
         chord = core.Chord()
         self.current_collection.collection[
            self.current_collection.collection.index(self._last_note)] = chord
         chord.collection.append(self._last_note)
         self._stack.append(self.current_collection)
         self.current_collection = chord
      self.add(note)
      self._last_note = note

   def add_Event_not_in_Chord(self, *args, **kwargs):
      note = core.EventFactory(*args, **kwargs)
      if isinstance(self.current_collection, core.Chord):
         self.reset_collection()
      self.add(note)
      self._last_note = note

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
         tag.tag(obj)

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


