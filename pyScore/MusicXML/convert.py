"""
Code to convert from pyGUIDO objects to MusicXML
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
from pyScore.elementtree.ElementTree import ElementTree
from guido_to_musicxml import GuidoToMusicXML

from types import StringType, UnicodeType

def guido_tree_to_musicxml_elementtree(score, warnings=False, verbose=False):
   assert isinstance(score, core.Score)
   converter = GuidoToMusicXML(warnings=warnings, verbose=verbose)
   return converter.convert(score)

def musicxml_elementtree_to_xml_elementtree(tree):
   return tree

def xml_elementtree_to_xml_file(tree, filename=None, output_encoding="ascii"):
   assert type(filename) in (StringType, UnicodeType)
   ElementTree(tree).write(open(filename, "wU"), output_encoding)

inputs = ["guido_tree", "musicxml_elementtree", "xml_elementtree"]
outputs = ["musicxml_elementtree", "xml_elementtree", "xml_file"]

