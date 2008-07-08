"""
Definition of 'Advanced GUIDO' fingering tag
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

class fingering(TAG):
    def __init__(self, name, id, args_list, args_dict, *args, **kwargs):
       TAG.__init__(self, name, id, args_list, args_dict, *args, **kwargs)
       if len(args_list) < 1 and not len(args_dict):
           self.raise_error("Invalid arguments to \\octave")
       if args_dict.has_key("text"):
          self.text = args_dict["text"]
       else:
          if not len(args_list):
             self.raise_error("You must give some fingering text.")
          self.text = args_list[0]
       if args_dict.has_key("dy"):
          self.dy = args_dict['dy']
       else:
          self.dy = None
       if args_dict.has_key("fsize"):
          self.fsize = args_dict['fsize']
       else:
          self.fsize = None

__all__ = """fingering""".split()
