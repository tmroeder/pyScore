"""
Definition of 'Basic GUIDO' clef tags
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

from pyScore.Guido.objects.core import TAG
import re

class clef(TAG):
    clef_names = {'treble': ('g', 2, 0),
                  'violino': ('g', 2, 0),
                  'bass': ('f', 4, 0),
                  'basso': ('f', 4, 0),
                  'tenor': ('c', 4, 0),
                  'alto': ('c', 3, 0)}
    default_lines = {'g': 2,
                     'f': 4,
                     'c': 3,
                     'perc': 3,
                     'gg': 2}
    regex = re.compile(r"(?P<type>(gg)|[gfc]|(perc)|)(?P<line>[1-5])?(?P<octave>(\+8)|(\-8)|(\+15)|(\-15))?$")
    
    def __init__(self, name, id, args_list, args_dict, *args, **kwargs):
        TAG.__init__(self, name, id, args_list, args_dict, *args, **kwargs)
        if len(args_list) < 1:
            self.raise_error("Invalid number of arguments on \\clef tag.")
        s = args_list[0]
        self.clef_name = s
        if self.clef_names.has_key(s):
            self.type, self.clef_line, self.octave = self.clef_names[s]
        else:
            match = self.regex.match(s)
            if match != None:
                match = match.groupdict()
                self.type = match['type']
                self.clef_line = match['line']
                self.octave = match['octave']
                if self.clef_line == None:
                    self.clef_line = self.default_lines[self.type]
                else:
                    self.clef_line = int(self.clef_line)
                if self.octave == None:
                    self.octave = 0
                else:
                    self.octave = int(self.octave)
            else:
                self.raise_error("Invalid clef name '%s'" % s)

__all__ = ['clef']
