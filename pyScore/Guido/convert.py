"""
Code to convert from Guido to Guido etc.
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
from pyScore.Guido.objects.basic import all as basic
from pyScore.Guido.objects.advanced import all as advanced
from pyScore.Guido.parser.guido_parser import GuidoParser
from pyScore.util.file_wrapper import *

from cStringIO import StringIO
import os
from os.path import exists, isfile
from types import StringType, UnicodeType

def guido_file_to_guido_string(input, input_encoding="utf8"):
   input = FileReader(input, input_encoding)
   return input.read()

def guido_string_to_guido_tree(s, warnings=False, trace=False):
   assert type(s) in (StringType, UnicodeType)
   parser = GuidoParser((core, basic, advanced), warnings=warnings, trace=trace)
   score = parser.parse(s)
   return score

def guido_tree_to_guido_string(score, output_encoding="utf8"):
   assert isinstance(score, core.Score)
   stream = FileWriter(StringIO(), output_encoding)
   score.write_guido(stream)
   return stream.getvalue()

def guido_tree_to_guido_file(score, filename=None, output_encoding="utf8"):
   assert isinstance(score, core.Score)
   output = FileWriter(filename, output_encoding)
   score.write_guido(output)

inputs = ["guido_file", "guido_string", "guido_tree"]
outputs = inputs

