"""
Code to convert from pyGUIDO objects to MusicXML
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
from pyScore.Guido.objects.basic import all as basic
from pyScore.Guido.objects.advanced import all as advanced
from pyScore.elementtree.ElementTree import ElementTree, iselement, parse
from pyScore.util.file_wrapper import *
from pyScore.__version__ import *

from guido_to_musicxml import GuidoToMusicXML
from musicxml_to_guido import MusicXMLToGuido

from types import StringType, UnicodeType

def guido_tree_to_musicxml_elementtree(score, warnings=False, verbose=False):
   assert isinstance(score, core.Score)
   converter = GuidoToMusicXML(warnings=warnings, verbose=verbose)
   return converter.convert(score)

def musicxml_elementtree_to_musicxml_file(tree, filename=None, output_encoding="ascii"):
   assert iselement(tree)
   ElementTree(tree).write(FileWriter(
      filename, output_encoding),
                           output_encoding, created,
      '<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 1.0 Partwise//EN" "http://www.musicxml.org/dtds/partwise.dtd">')

def musicxml_file_to_musicxml_elementtree(file):
   tree = parse(file)
   return tree.getroot()

def musicxml_elementtree_to_guido_tree(tree, warnings=False, verbose=False):
   assert iselement(tree)
   converter = MusicXMLToGuido((core, basic, advanced), warnings=warnings, verbose=verbose)
   return converter.convert(tree)

inputs = ["guido_tree", "musicxml_elementtree", "musicxml_file"]
outputs = inputs

