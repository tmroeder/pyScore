"""
Various type conversion and range checking functions

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

def int_range_check(s, min, max, message, warnings):
   try:
      i = int(s)
   except ValueError:
      warnings.append("'%s' in %s can not be converted to an integer." % (s, message))
      i = min
   if i < min or i > max:
      warnings.append("'%d' in %s is out of range (%d - %d)." % (i, message, min, max))
      if i < min:
         i = min
      else:
         i = max
   return i
      