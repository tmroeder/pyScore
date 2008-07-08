"""
Definition of 'Basic GUIDO' beam and stem tags
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

from pyScore.Guido.objects.core import TAG, Note

class beam(TAG):
    def __init__(self, name, id, args_list, args_dict, *args, **kwargs):
       TAG.__init__(self, name, id, args_list, args_dict, *args, **kwargs)
       # NOTE: arguments to Guido beams are ignored

bm = beam

class stemsAuto(TAG):
    pass

class stemsUp(TAG):
    pass

class stemsDown(TAG):
    pass

__all__ = """
beam bm stemsAuto stemsUp stemsDown
""".split()
