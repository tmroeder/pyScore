"""
Tools for interacting with the Guido NoteServer
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

from urllib import urlencode, urlopen

NOTESERVER = "http://tempo.iti.informatik.tu-darmstadt.de/scripts/salieri/gifserv.pl"

def get_url_args(gmn_string, width="16.0cm", height="12.0cm", zoom=0.5, **kwargs):
   """Get the CGI arguments to send to the GUIDO noteserver"""
   return urlencode({'defph': str(height),
                     'defpw': str(width),
                     'zoom': str(zoom),
                     'mode': 'gif',
                     'gmndata': gmn_string})
   
def get_url(gmn_string, server=NOTESERVER, **kwargs):
   """Get the URL to get a rendering of the given GMN string from the Guido Noteserver.
An alternate Noteserver can be specified with the server argument."""
   return server + "?" + get_url_args(gmn_string, **kwargs)

def get_gif_handle(gmn_string, server=NOTESERVER, **kwargs):
   """Gets a file handle to a GIF file of a rendering of the given GMN string from the Guido Noteserver.
An alternate Noteserver can be specified with the server argument."""
   return urlopen(server, get_url_args(gmn_string, **kwargs))

def save_gif(gmn_string, filename, **kwargs):
   """Saves a rendering of the given GMN string from the Guido Noteserver to the given filename.
An alternate Noteserver can be specified with the server argument."""
   open(filename, "wb").write(get_gif_handle(gmn_string, **kwargs).read())
   
