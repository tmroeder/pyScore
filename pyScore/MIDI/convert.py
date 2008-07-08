"""
Code to convert from MusicXML -> MIDI XML -> MIDI
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
from pyScore.util.file_wrapper import *
from pyScore.__version__ import *

from musicxml_to_midixml import MusicXMLToMidiXML
from midixml_to_midi import MidiXMLToMidi
from validate import validate

from cStringIO import StringIO
import os
from os.path import exists, isfile
from types import *

config.add_option("", "--xml-encoding", action="store", default="us-ascii", help="[xml] The encoding to save XML files.")
config.add_option("", "--dtd", action="store_true", help="[xml] validate against a DTD.")

def MidiXML_file_to_MidiXML_tree(file):
   if config.get("dtd") and type(file) in (StringType, UnicodeType):
      validate(file)
   tree = ElementTree.parse(file)
   return tree.getroot()

def MusicXML_tree_to_MidiXML_tree(tree):
   assert ElementTree.iselement(tree)
   converter = MusicXMLToMidiXML()
   return converter.convert(tree)

def MidiXML_tree_to_MidiXML_file(tree, filename=None):
   assert ElementTree.iselement(tree)
   output_encoding = config.get("xml_encoding")
   writer = FileWriter(filename, output_encoding)
   writer.write("<?xml version='1.0' encoding='%s'?>\n" % output_encoding)
   writer.write("<!-- %s -->\n" % created)
   writer.write('<!DOCTYPE MIDIFile PUBLIC "-//Recordare//DTD MusicXML 1.0 MIDI//EN" "http://www.musicxml.org/dtds/midixml.dtd">\n')

   ElementTree.ElementTree(tree).write(writer)
   if config.get("dtd"):
      validate(filename)

def MidiXML_tree_to_MIDI_stream(tree):
   assert ElementTree.iselement(tree)
   converter = MidiXMLToMidi()
   stream = StringIO()
   converter.convert(tree, stream)
   return stream.getvalue()

def MidiXML_tree_to_MIDI_file(tree, filename=None):
   assert ElementTree.iselement(tree)
   converter = MidiXMLToMidi()
   converter.convert(tree, open(filename, "wb"))

## def MIDI_file_to_MidiXML_tree(tree):
##    raise NotImplementedError()

inputs = ["MusicXML_tree", "MidiXML_tree", "MidiXML_file"]
outputs = ["MidiXML_tree", "MidiXML_file", "MIDI_file", "MIDI_stream"]

