"""
Provides an extended option parser that loads options from a file and then
overrides them with options on the command line

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

from util.config import *

from inspect import getfile
from os.path import split, join, expanduser

class PyScoreConfigOptionParser(ConfigOptionParser):
   default_options = ConfigOptionParser.default_options + [
      make_option("-w", "--warnings", action="store_true",
                  help="[general] Display warnings"),
      make_option("-v", "--verbose", action="store_true",
                  help="[general] Verbose feedback"),
      make_option("-t", "--trace", action="store_true",
                  help="[general] Trace the actions of the parser")]

   def get_config_files(self):
      dir = split(getfile(PyScoreConfigOptionParser))[0]
      return [join(dir, "pyScore.cfg"), join(expanduser("~"), ".pyScore")]

config = PyScoreConfigOptionParser()

__all__ = ["config"]
