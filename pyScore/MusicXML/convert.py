"""
Code to convert from pyGUIDO objects to MusicXML
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
from pyScore import ElementTree
from pyScore.Guido.objects import core
from pyScore.Guido.objects.basic import all as basic
from pyScore.Guido.objects.advanced import all as advanced
from pyScore.util.file_wrapper import *
from pyScore.__version__ import *

from guido_to_musicxml import GuidoToMusicXML
from musicxml_to_guido import MusicXMLToGuido
from validate import validate

from types import *

config.add_option("", "--xml-encoding", action="store", default="us-ascii", help="[xml] The encoding to save XML files.")
config.add_option("", "--dtd", action="store_true", help="[xml] validate against a DTD.")

def Guido_tree_to_MusicXML_tree(score):
   assert isinstance(score, core.Score)
   converter = GuidoToMusicXML()
   return converter.convert(score)

def MusicXML_tree_to_MusicXML_file(tree, filename=None):
   assert ElementTree.iselement(tree)
   output_encoding = config.get("xml_encoding")
   writer = FileWriter(filename, output_encoding)
   writer.write("<?xml version='1.0' encoding='%s'?>\n" % output_encoding)
   writer.write("<!-- %s -->\n" % created)
   writer.write('<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 1.0 Partwise//EN" "http://www.musicxml.org/dtds/partwise.dtd">\n')

   ElementTree.ElementTree(tree).write(writer)
   if config.get("dtd"):
      validate(filename)

def MusicXML_file_to_MusicXML_tree(file):
   if config.get("dtd") and type(file) in (StringType, UnicodeType):
      validate(file)
   tree = ElementTree.parse(file)
   return tree.getroot()

def MusicXML_tree_to_Guido_tree(tree):
   assert ElementTree.iselement(tree)
   converter = MusicXMLToGuido((core, basic, advanced))
   return converter.convert(tree)

inputs = ["Guido_tree", "MusicXML_tree", "MusicXML_file"]
outputs = inputs

