"""
Definition of 'Basic GUIDO' meter tags
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
import re

class meter(TAG):
    _regex_meter = re.compile(r"(?P<num>[0-9]+)/(?P<den>[0-9]+)")
    named_meters = {'C': '4/4',
                    'C/': '2/2'}

    def __init__(self, name, id, args_list, args_dict, *args, **kwargs):
        TAG.__init__(self, name, id, args_list, args_dict, *args, **kwargs)
        if len(args_list) < 1 and not args_dict.has_key('type'):
            self.raise_error("Invalid number of arguments on \\meter tag.")
        if len(args_list):
            s = args_list[0]
        else:
            s = args_dict['type']
        self.parse_meter(s)

    def parse_meter(self, s):
        if self.named_meters.has_key(s.upper()):
            self.named_meter = s.upper()
            fraction = self.named_meters[self.named_meter]
        else:
            self.named_meter = None
            fraction = s
        match = self._regex_meter.match(fraction)
        if not match:
            self.raise_error(
                "'%s' is not a valid meter specification." % s)
        else:
            d = match.groupdict()
            self.num = int(d['num'])
            self.den = int(d['den'])

__all__ = ['meter']
