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
from pyScore import ElementTree
from pyScore.Guido.objects import core
from pyScore.Guido.objects.basic import all as basic
from pyScore.Guido.objects.advanced import all as advanced
from pyScore.util.file_wrapper import *
from pyScore.__version__ import *

from guido_to_lilypond import GuidoToLilypond
#from validate import validate

from types import *

def Guido_tree_to_Lilypond_tree(score):
   assert isinstance(score, core.Score)
   converter = GuidoToLilypond()
   return converter.convert(score)

def Lilypond_tree_to_Lilypond_file(score, filename=None):
   output_encoding = "UTF8"
   writer = FileWriter(filename, output_encoding)
   writer.write(created + "\n")
   for i in score:
      writer.write(str(i))

inputs = ["Guido_tree", "Lilypond_tree"]
outputs = ["Lilypond_tree", "Lilypond_file"]
