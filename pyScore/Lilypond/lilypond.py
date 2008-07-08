"""
LilyPond Objects
Python GUIDO tools

Copyright (C) 2004 Michael Droettboom
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

from pyScore.util.Rat import rat




# The Lilypond tree is a list of LilypondElements
# When an element's contents is:
# - A string, the form is '\item string'
# - A list, the form is '\item { }'
# (TODO: This needs to be refactored into LilypondCommand and LilypondExpression)

class LilypondElement:
   def __init__(self, name='', contents=None):
      self.name = name
      self.contents = contents

   def __repr__(self, indent='', prev_element=None):
      s = ''
      if self.name:
         s += '\n' + indent + '\\'+self.name+' '
      if isinstance(self.contents, LilypondElement):
         if (prev_element): s += ' '
         s += self.contents.__repr__(indent+'  ')
      elif isinstance(self.contents, str) or isinstance(self.contents, unicode):
         if (prev_element): s += ' '
         s += self.contents
      elif isinstance(self.contents, list):
         if (prev_element): s += ' '
         s += '{\n'
         prev = None
         s += indent + '  '
         for i in self.contents:
            s += i.__repr__(indent+'  ', prev)
            prev = i
         s += '\n'
         s += indent + '}'
      elif isinstance(self.contents, tuple):
         if (prev_element): s += ' '
         prev = None
         for i in self.contents:
            if isinstance(i, LilypondElement):
               s += i.__repr__(indent+'  ', prev) + ' '
            elif isinstance(i, str) or isinstance(i, unicode):
               if prev: s += ' '
               s += i
            prev = i
      return s

# When the contents of a LilypondElement is a list,
# it must contain LilypondElements.  However, if
# a list of notes is desired, it will contain
# LilypondNotes which override the string
# representation in the Lilypond notation format

LilypondNoteAttributes = {'tempo': None, 'dynamics': None}

class LilypondNote(LilypondElement):
   def __init__(self, pitch=0, duration=0, dotting=0, attributes=None):
      LilypondElement.__init__(self, None, None)
      self.pitch = pitch
      self.duration = duration
      self.dotting = dotting
      if attributes:
         self.attributes = attributes
      else:
         self.attributes = LilypondNoteAttributes.copy()

   def __repr__(self, indent='', prev_element=None, show_duration=True):
      s = ''
      if (prev_element): s += ' '
      s += self.pitch
      if not (isinstance(prev_element, LilypondNote)
          and prev_element.duration == self.duration
              and prev_element.dotting == self.dotting) and show_duration:
         s += str(self.duration.den)
         for i in range(self.dotting):
            s += '.'
      s += self.str_attribs()
      return s

   def str_attribs(self):
      attribs = ''
      for i in self.attributes:
         if self.attributes[i]:
            attribs += self.attributes[i]
      return attribs

# Header information is in the form of tags,
# represented as 'tag = "string"'

class LilypondTag(LilypondElement):
   def __repr__(self, indent='', prev_element=None):
      s = ''
      if prev_element: s += ' '
      if self.name:
         s += self.name+' = '
      if isinstance(self.contents, str) or isinstance(self.contents, unicode):
         s += '"'+self.contents+'"'
      return s

# Sometimes Scheme commands need to be
# sent to Lilypond's interpreter to
# affect internal variables
# ex. octavation

class LilypondScheme(LilypondElement):
   def __repr__(self, indent='', prev_element=None):
      s = '#('+self.name+' '+str(self.contents)+')'
      return s


# Parallel elements contain staves and polyphonic
# parts that run in parallel. Denoted by '<< >>'
# Same staff denoted by '\\'

class LilypondParallel(LilypondElement):
   def __init__(self, name='', contents=None, same_staff=False):
      LilypondElement.__init__(self, name, contents)
      self.same_staff = same_staff

   def __repr__(self, indent='', prev_element=None):
      s = '<<\n'

      output_same_staff_marker = self.same_staff

      prev = None
      for i in self.contents:
         s += indent + '  ' + i.__repr__(indent+'  ', prev)+'\n'
         if output_same_staff_marker:
            s += indent + '  \\\\\n'
            output_same_staff_marker = False
         prev = i

      s += indent + '>>'
      return s

class LilypondChord(LilypondNote):
   def __init__(self, contents=None, duration=0, attributes=None):
      LilypondNote.__init__(self, None, duration, attributes)
      LilypondElement.__init__(self, None, contents)

   def __repr__(self, indent='', prev_element=None):
      s = ''
      if (prev_element): s += ' '
      s += '<'
      prev = None
      for i in self.contents:
         if isinstance(i, LilypondNote):
            s += i.__repr__('', prev, False)
            prev = i
         else:
            s += str(i)
      s += '>' + str(self.duration.den) + self.str_attribs()
      return s

class LilypondBarline(LilypondElement):
   def __init__(self):
      pass

   def __repr__(self, indent='', prev_element=None):
      s = ''
      if prev_element: s += ' '
      s += '|\n' + indent
      return s

class LilypondGroup(LilypondElement):
   def __init__(self, contents=None):
      self.contents = contents
      self.leftbracket = ''
      self.rightbracket = ''
      self.first_outside = False

   def __repr__(self, indent='', prev_element=None):
      contents = self.contents
      s = ''
      if prev_element: s += ' '

      prev = None
      if self.first_outside:
         s += self.contents[0].__repr__(indent+'  ', None)
         prev = self.contents[0]
         contents = self.contents[1:]

      s += self.leftbracket
      for i in contents:
         s += i.__repr__(indent+'  ', prev)
         prev = i
      s += self.rightbracket
      return s

class LilypondSlur(LilypondGroup):
   def __init__(self, contents=None):
      LilypondGroup.__init__(self, contents)
      self.first_outside = True

   def __repr__(self, indent='', prev_element=None):
      # Recursively check if this element contains another slur, in
      # which case this should be represented as a phrasing slur.
      # Note: Better to do this here or at creation time?
      #       Ideally, only when contents is modified.
      if self.contains_slur(self.contents):
         self.leftbracket = '\('
         self.rightbracket = '\)'
      else:
         self.leftbracket = '('
         self.rightbracket = ')'
      return LilypondGroup.__repr__(self, indent, prev_element)

   def contains_slur(self, contents):
      if not contents:
         return False
      for i in contents:
         if isinstance(i, LilypondSlur):
            return True
         elif (isinstance(i, LilypondElement)
               and self.contains_slur(i.contents)):
            return True

class LilypondTie(LilypondGroup):
   def __init__(self, contents=None):
      LilypondGroup.__init__(self, contents)
      self.leftbracket = '~'
      self.first_outside = True

class LilypondBeam(LilypondGroup):
   def __init__(self, contents=None):
      LilypondGroup.__init__(self, contents)
      self.leftbracket = '['
      self.rightbracket = ']'
      self.first_outside = True

class LilypondTrill(LilypondGroup):
   def __init__(self, contents=None):
      LilypondGroup.__init__(self, contents)
      self.leftbracket = '\\trill'
      self.first_outside = True

class LilypondStaccato(LilypondGroup):
   def __init__(self, contents=None):
      LilypondGroup.__init__(self, contents)
      self.leftbracket = '-.'
      self.first_outside = True

class LilypondTenuto(LilypondGroup):
   def __init__(self, contents=None):
      LilypondGroup.__init__(self, contents)
      self.leftbracket = '--'
      self.first_outside = True

class LilypondAccent(LilypondGroup):
   def __init__(self, contents=None):
      LilypondGroup.__init__(self, contents)
      self.leftbracket = '->'
      self.first_outside = True

class LilypondFermata(LilypondGroup):
   def __init__(self, contents=None):
      LilypondGroup.__init__(self, contents)
      self.leftbracket = '^\\fermata'
      self.first_outside = True

class LilypondMordent(LilypondGroup):
   def __init__(self, contents=None):
      LilypondGroup.__init__(self, contents)
      self.leftbracket = '\\mordent'
      self.first_outside = True

class LilypondTurn(LilypondGroup):
   def __init__(self, contents=None):
      LilypondGroup.__init__(self, contents)
      self.leftbracket = '\\turn'
      self.first_outside = True

class LilypondCrescendo(LilypondGroup):
   def __init__(self, contents=None):
      LilypondGroup.__init__(self, contents)
      self.leftbracket = '\\>'
      self.rightbracket = '\\!'
      self.first_outside = True

class LilypondDiminuendo(LilypondGroup):
   def __init__(self, contents=None):
      LilypondGroup.__init__(self, contents)
      self.leftbracket = '\\<'
      self.rightbracket = '\\!'
      self.first_outside = True

class LilypondDynamic(LilypondGroup):
   def __init__(self, mark, contents=None):
      self.mark = mark
      LilypondGroup.__init__(self, contents)
      self.leftbracket = '\\'+mark
      self.first_outside = True

class LilypondTremolo(LilypondGroup):
   def __init__(self, contents=None, subdivision=32):
      LilypondGroup.__init__(self, contents)
      self.subdivision = subdivision

      if contents:
         notes = len(contents)
         if (notes > 1):
            total_duration = rat(0)
            for i in contents:
               if isinstance(i, LilypondNote):
                  total_duration += i.duration
            # TODO: check this part
            for i in contents:
               if isinstance(i, LilypondNote):
                  i.duration *= total_duration / notes
            self.duration = total_duration

   def __repr__(self, indent='', prev_element=None):
      if len(self.contents)<=1:
         self.leftbracket = ':' + str(self.subdivision)
         self.first_outside = True
         return LilypondGroup.__repr__(self, indent, prev_element)
      else:
         self.leftbracket = '{'
         self.rightbracket = '}'
         self.first_outside = False
         s = ''
         if prev_element: s += ' '
         s += '\\repeat "tremolo" %d'%self.duration.den
         s += LilypondGroup.__repr__(self, indent, prev_element)
         return s

class LilypondTextSpanner(LilypondGroup):
   def __init__(self, text=None, contents=None):
      LilypondGroup.__init__(self, contents)
      self.leftbracket = '\\startTextSpan'
      self.rightbracket = '\\stopTextSpan'
      self.first_outside = True
      self.text = text

   def __repr__(self, indent='', prev_element=None):
      s = '\n'+indent
      s += '\\override TextSpanner #\'edge-text = #\'("%s")\n'%self.text
      s += indent + LilypondGroup.__repr__(self, indent, None)
      s += '\n' + indent
      return s
