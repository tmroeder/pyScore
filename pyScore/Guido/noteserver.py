"""
Tools for interacting with Guido NoteServer
Python GUIDO tools

Copyright (C) 2002 Michael Droettboom
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

from urllib import urlencode

def get_url(gmn_string):
   url = "http://tempo.iti.informatik.tu-darmstadt.de/scripts/salieri/gifserv.pl?"
   url += urlencode({'defph': '12.0cm',
                     'defpw': '16.0cm',
                     'zoom': '0.5',
                     'mode': 'gif',
                     'gmndata': gmn_string})
   return url
