#!/usr/bin/env python

"""Python Score utilities distutils script.

(c) 2004 Michael Droettboom"""

# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#

from distutils.core import setup, Extension
from distutils.sysconfig import get_python_lib, get_python_inc, PREFIX
from glob import glob
from os.path import walk, split, join, isdir
import sys

from pyScore.__version__ import *

########################################
# Packages

packages = []
if sys.platform != 'win32':
   def visit(arg, dirname, names):
      if '__init__.py' in names:
         packages.append(".".join(dirname.split("/")))
else:
   def visit(arg, dirname, names):
      if '__init__.py' in names:
         packages.append(".".join(dirname.split("\\")))
walk("pyScore", visit, ())

########################################
# Scripts

scripts = [x for x in glob(join("scripts", "*"))
           if not isdir(x) and not '~' in x]

########################################
# Data

lib_path = get_python_lib()[len(PREFIX)+1:]
data_dirs = ["pyScore.MusicXML.DTD", "pyScore.MusicXML.XSLT"]
data_files = []
for dir in data_dirs:
   dir = join(*dir.split("."))
   files = glob(join(dir, "*.*"))
   data_files.append((join(lib_path, dir), files))

########################################
# Extensions

if "--no-compiler" in sys.argv:
   extensions = []
else:
   extensions = [Extension("pyScore.util.crat", ["src/crat/cratmodule.c"],
                           define_macros=[('NDEBUG', 1)])]

setup(name = "pyScore",
      version = version,
      url = url,
      author = author,
      author_email = "mdboom@jhu.edu",
      packages = packages,
      scripts = scripts,
      data_files = data_files,
      ext_modules=extensions
      )
