"""
Validates a given XML filename against the MusicXML DTD
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

from inspect import getfile
from os import system
from os.path import split, join

def validate(filename):
   dir = split(getfile(validate))[0]
   # TODO: check that we have ``xmllint`` and use it
   val = system("xmllint --dtdvalid %s --noout %s" % (join(dir, "DTD", "partwise.dtd"), filename))
   print "XMLLINT returned:", val
   return val
   
