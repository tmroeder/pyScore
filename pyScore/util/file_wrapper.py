"""
A general wrapper around files for compression and en/decoding support

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

from os.path import splitext
import codecs
from types import *

def FileWriter(filename, encoding="utf8"):
    if type(filename) in (StringType, UnicodeType):
        if splitext(filename)[1] == "bz2":
            import bzip2
            fd = bzip2.BZ2File(filename, "w")
        elif splitext(filename)[1] == "gz":
            import gzip
            fd = gzip.GzipFile(filename, "w")
        else:
            fd = file(filename, "w")
    elif hasattr(fd, 'write'):
        fd = filename
    else:
        raise ValueError("Argument 1 of 'FileWriter' is not a filename or file object.")
    writer = codecs.getwriter(encoding)(fd, 'replace')
    return writer

def FileReader(filename, encoding="utf8"):
    if type(filename) in (StringType, UnicodeType):
        if splitext(filename)[1] == "bz2":
            import bzip2
            fd = bzip2.BZ2File(filename, "rU")
        elif splitext(filename)[1] == "gz":
            import gzip
            fd = gzip.GzipFile(filename, "rU")
        else:
            fd = file(filename, "rU")
    elif hasattr(fd, 'read'):
        fd = filename
    else:
        raise ValueError("Argument 1 of 'FileReader' is not a filename or file object.")
    return codecs.getreader(encoding)(fd)

