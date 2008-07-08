"""
Definition of 'Basic GUIDO' key tags
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

class key(TAG):
    tag_category = 'key'

    # It's faster and easier to just hard-code this stuff
    # than to generate it at run-time.

    key_names_to_num_sharps_or_flats = {
        'C': 0,   'C#': 7, 'D&': -5, 'D': 2,   'E&': -3,
        'E': 4,   'F': -1, 'F#': 6,  'G&': -7, 'G': 1,
        'A&': -4, 'A': 3,  'B&': -2, 'B': 5,
        'a': 0,   'a#': 7, 'b&': -5, 'b': 2,   'c': -3,
        'c#': 4,  'd': -1, 'd#': 6,  'a&': -7, 'e': 1,
        'e&': -6,
        'f': -4,  'f#': 3, 'g': -2,  'g#': 5 }

    def __init__(self, name, id, args_list, args_dict, *args, **kwargs):
        TAG.__init__(self, name, id, args_list, args_dict, *args, **kwargs)
        if len(args_list) < 1:
            self.raise_error("Invalid number of arguments on \key tag.")
        s = args_list[0]
        try:
            self.key_mode = None
            self.num_sharps_or_flats = int(s)
        except:
            if self.key_names_to_num_sharps_or_flats.has_key(s):
                self.num_sharps_or_flats = (
                    self.key_names_to_num_sharps_or_flats[s])
                if s == s.upper():
                    self.key_mode = "major"
                else:
                    self.key_mode = "minor"
            else:
                self.raise_error(
                    "%s is an invalid key name." % s)

__all__ = ['key']
