"""
Code to convert from MusicXML to GUIDO
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

from pyScore.util.structures import *
from pyScore.Guido.objects import core
from pyScore.Guido.objects.basic import all as basic
from pyScore.Guido.objects.advanced import all as advanced
from pyScore.util.rational import Rat

from pyScore.elementtree.ElementTree import iselement

class MusicXMLToGuido:
   def __init__(self, warnings=True, verbose=False):
       self._warnings = warnings
       self._verbose = verbose

   def convert(self, tree):
       assert iselement(tree)
       self.make_plan(tree)

   def make_plan(self, tree):
       
