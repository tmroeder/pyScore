# vi:set tabsize=3:
"""
Definition of 'Advanced GUIDO' text tags
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

from pyScore.Guido.objects import core
from pyScore.Guido.objects.basic.text import TEXT

class lyrics(TEXT):
   def __init__(self, name, id, args_list, args_dict, *args, **kwargs):
      TEXT.__init__(self, name, id, args_list, args_dict, *args, **kwargs)
      self.parse_lyrics()

   def parse_lyrics(self):
      text = self.text.replace("-", "- -").replace("_", "_ _")
      self.syllables = [x.replace("~", " ").replace("__", "_")
                        for x in text.split()]

   def get_syllable(self, note):
      """We need to figure out which syllable this note corresponds
      to, ignoring all tags, rests and other elements.  This is a
      time consuming process, but is the most straightforward, since
      we would not get the notes in nested tags through 'append'.
      """
      i = 0
      for item in self.events:
         if isinstance(item, core.Note) or isinstance(item, core.Chord):
            if item == note:
               return self.syllables[i], (i == len(self.syllables) - 1)
            i += 1
         if i >= len(self.syllables):
            break
      # We fail silently
      return "", False

#   self.raise_error("Too many notes for lyric:\n '%s'" % ('/'.join(self.syllables)))
#   self.raise_error("Error matching syllables to notes:\n '%s'" % ('/'.join(self.syllables)))
      
__all__ = """
lyrics
""".split()
