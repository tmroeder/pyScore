"""
Python Score tools

This script builds the (very simple) website.

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

try:
   from docutils.core import publish_file
except ImportError, e:
   print "'docutils' 0.3 or later must be installed to generate the documentation."
   print "It can be downloaded at http://docutils.sf.net"
   sys.exit(1)

from pyScore.__version__ import __version__
from pyScore.util.source import get_notes

from cStringIO import StringIO
from glob import glob
from os import mkdir, stat
from os.path import isdir, isfile, join, split

DIST_DIR = join("..", "dist")
SRC_DIR = join("..", "pyScore")
README = join("..", "README")

files = []
file_types = ['zip', 'bz2', 'gz']
for type in file_types:
   files.extend(glob(join(DIST_DIR, "*." + type)))
files.sort()

downloads = []
for file in files:
   file_size = stat(file).st_size
   file_root = split(file)[1]
   downloads.append('- `%s <%s>`_ (%d bytes)\n' % (file_root, file_root, file_size))
source = open("index.txt", "r").read()

release_notes = get_notes(SRC_DIR)

parts = {"downloads": ''.join(downloads),
         "version": __version__,
         "release_notes": release_notes }

filled_in = source % parts

if not isfile(README) or filled_in != open(README, "r").read():
   open(README, "w").write(filled_in)

fd = StringIO(filled_in)
publish_file(source=fd, destination=open(join(DIST_DIR, "index.html"), "w"), writer_name="html")

if isfile("tests.txt"):
   publish_file(source=open("tests.txt", "rU"),
                destination=open(join(DIST_DIR, "tests.html"), "w"),
                writer_name="html")

open(join(DIST_DIR, "default.css"), "w").write(open("default.css", "r").read())
