"""
Definition of 'Basic GUIDO' text tags
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

class TEXT(TAG):
    def __init__(self, name, id, args_list, args_dict, *args, **kwargs):
       TAG.__init__(self, name, id, args_list, args_dict, *args, **kwargs)
       if len(args_list) < 1 and not args_dict.has_key("name"):
          self.raise_error("Invalid arguments for \\%s" % name)
       if len(args_list):
           self.text = args_list[0]
       if args_dict.has_key("name"):
           self.text = args_dict['name']

class text(TEXT):
    pass
t = text

class label(TEXT):
    pass
    
class title(TEXT):
    pass

class composer(TEXT):
    pass

class mark(TEXT):
    pass

class lyricist(TEXT):
    pass

__all__ = """
text t label title composer mark lyricist
""".split()
