"""
Definition of 'Basic GUIDO' cue and grace tags
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

from pyScore.Guido.objects.core import TAG
from pyScore.util.rational import Rat

class grace(TAG):
    def __init__(self, name, id, args_list, args_dict, *args, **kwargs):
       TAG.__init__(self, name, id, args_list, args_dict, *args, **kwargs)
       if len(args_list) > 1 or len(args_dict):
          self.raise_error("Invalid arguments for \\grace")
       if len(args_list) == 1:
          self.duration = Rat(1, int(args_list[0]))
       else:
          self.duration = Rat(1, 32)

class cue(TAG):
    def __init__(self, name, id, args_list, args_dict, *args, **kwargs):
       TAG.__init__(self, name, id, args_list, args_dict, *args, **kwargs)
       if len(args_list) > 1 or len(args_dict):
          self.raise_error("Invalid arguments for \\cue")
       if len(args_list) == 1:
          self.instrument = args_list[0]
       else:
          self.instrument = ""

__all__ = """
cue grace
""".split()
