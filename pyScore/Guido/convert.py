"""
Code to convert from Guido to Guido etc.
Python GUIDO tools

Copyright (C) 2002 Michael Droettboom

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
 
You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
"""

from pyScore.Guido.objects import core
from pyScore.Guido.objects.basic import all as basic
from pyScore.Guido.objects.advanced import all as advanced
from pyScore.Guido.parser.guido_parser import GuidoParser

from cStringIO import StringIO
import os
from types import StringType, UnicodeType

def guido_file_to_guido_string(input, input_encoding="utf8"):
   assert type(input) in (StringType, UnicodeType)
   if not os.path.exists(input):
      raise IOError("'%s' not found." % input)
   return open(input, "rU").read().decode(input_encoding)

def guido_string_to_guido_tree(s, warnings=False, trace=False):
   assert type(s) in (StringType, UnicodeType)
   score = GuidoParser((core, basic, advanced), warnings=warnings, trace=trace).parse(s)
   score.calc_time_spines()
   return score

def guido_tree_to_guido_string(score, output_encoding="utf8"):
   assert isinstance(score, core.Score)
   from codecs import getwriter
   stream = StringIO()
   score.write_guido(getwriter(output_encoding)(stream))
   return stream.getvalue()

def guido_tree_to_guido_file(score, filename=None, output_encoding="utf8"):
   assert isinstance(score, core.Score)
   assert type(filename) in (StringType, UnicodeType)
   from codecs import getwriter
   stream = open(filename, "w")
   score.write_guido(getwriter(output_encoding)(stream))

inputs = ["guido_file", "guido_string", "guido_tree"]
outputs = ["guido_tree", "guido_string", "guido_file"]

