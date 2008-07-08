"""
Code to convert from Guido to Guido etc.
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

from pyScore.config import config
from pyScore.Guido.objects import core
from pyScore.Guido.objects.basic import all as basic
from pyScore.Guido.objects.advanced import all as advanced
from pyScore.Guido.parser.guido_parser import GuidoParser
from pyScore.Guido.noteserver import save_gif
from pyScore.util.file_wrapper import *
from pyScore.__version__ import *

from cStringIO import StringIO
import os
from os.path import exists, isfile
from types import StringType, UnicodeType

# NOTE: Guido is output with latin_1 encoding, because that seems to work with NoteServer

config.add_option("", "--guido-encoding", action="store", default="latin_1", help="[guido] The encoding for Guido files")

def Guido_file_to_Guido_string(input):
   input = FileReader(input, config.get("guido_encoding"))
   return input.read()

def Guido_string_to_Guido_tree(s):
   assert type(s) in (StringType, UnicodeType)
   parser = GuidoParser((core, basic, advanced))
   score = parser.parse(s)
   return score

def Guido_tree_to_Guido_string(score):
   assert isinstance(score, core.Score)
   stream = FileWriter(StringIO(), config.get("guido_encoding"))
   stream.write("% " + created + "\n")
   score.write_guido(stream)
   return stream.getvalue()

def Guido_tree_to_Guido_file(score, filename=None):
   assert isinstance(score, core.Score)
   output = FileWriter(filename, config.get("guido_encoding"))
   output.write("% " + created + "\n")
   score.write_guido(output)

def Guido_string_to_Guido_image(gmn_string, filename=None):
   save_gif(gmn_string, filename, width=config.get("width"), height=config.get("height"), zoom=config.get("zoom"))

inputs = ["Guido_file", "Guido_string", "Guido_tree"]
outputs = ["Guido_file", "Guido_string", "Guido_tree", "Guido_image"]

