"""
Helpers for the scipts
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

from glob import glob
try:
   from optparse import OptionParser
except ImportError:
   from pyScore.util.backport.optparse import OptionParser
try:
   import textwrap
except ImportError:
   from pyScore.util.backport import textwrap
from os.path import splitext, split, join, exists, isdir, isfile
import os
import sys

class ConverterOptions:
   def __init__(self, input_format, output_format, extra_args=None, description=None):
      if description == None:
         description = "Converts %s to %s" % (input_format, output_format)
      parser = OptionParser(description + "\nusage: \%prog [-o=output_file] [-w] [-v] [-t] input_file")

      parser.add_option("-o", "--output", dest="output",
                        help="Output file in %s format" % output_format)
      parser.add_option("-w", "--warnings", action="store_true", dest="warnings",
                        help="Display warnings")
      parser.add_option("-v", "--verbose", action="store_true", dest="verbose",
                        help="Verbose feedback")
      parser.add_option("-t", "--trace", action="store_true", dest="trace",
                        help="Trace the actions of the parser")
      if extra_args:
         for arg, kwargs in extra_args:
            parser.add_option(*arg, **kwargs)
      (options, args) = parser.parse_args()

      if len(args) < 1:
         parser.error("No input file(s) specified")
      self.input_files = []
      for arg in args:
         self.input_files.extend(glob(arg))
      if not len(self.input_files):
         parser.error("Cannot find input file(s) '%s'" % " ".join(args))
      if options.output != "":
         if len(self.input_files) != 1:
            parser.error("Cannot specify an output file when converting multiple files.")
         self.output_file = options.output
      self.options = options

   def __getattr__(self, attr):
      return getattr(self.options, attr)

class Format:
   def __init__(self, name, ext, converter):
      self.name = name
      self.ext = ext
      self.converter = converter

def convert(modules, input_format, output_format,
            extra_args=None, callback=None):
   from pyScore.convert import ConverterGraph
   assert isinstance(input_format, Format)
   assert isinstance(output_format, Format)
   options = ConverterOptions(
      "%s (.%s)" % (input_format.name, input_format.ext),
      "%s (.%s)" % (output_format.name, output_format.ext),
      extra_args=extra_args)

   converter = ConverterGraph(modules)
   steps = converter.get_steps(input_format.converter, output_format.converter)

   for filename in options.input_files:
      if options.output_file:
         output = options.output_file
      else:
         output = splitext(filename)[0] + "." + output_format.ext
      print "Converting '%s' to '%s'..." % (split(filename)[1], split(output)[1])
      sys.stdout.flush()
      converter.run_steps(
         steps, filename, filename=output,
         warnings=options.warnings, verbose=options.verbose)
      if callback:
         callback(options, filename, output)

def test(modules, test_dir, tests, groundtruth=False, callback=None):
   if len(sys.argv) > 1:
      if isdir(sys.argv[-1]):
         test_dir = sys.argv[-1]
   if not isdir(test_dir):
      print "Test directory '%s' can not be found." % TEST_DIRECTORY
      sys.exit(1)

   from pyScore.convert import ConverterGraph
   converter = ConverterGraph(modules)
   groundtruth_warnings = []
   for dir, input_format, output_format in tests:
      root_dir = join(test_dir, dir)
      if not isdir(root_dir):
         raise IOError("No test directory '%s'" % root_dir)
      input_dir = join(root_dir, "input")
      if not isdir(input_dir):
         raise IOError("No test input directory '%s'" % test_root)
      output_dir = join(root_dir, "output")
      if not exists(output_dir):
         os.mkdir(output_dir)
      if not isdir(output_dir):
         raise IOError("No test output directory '%s'" % output_dir)
      if groundtruth:
         gt_dir = join(root_dir, "groundtruth")
         if not isdir(gt_dir):
            raise IOError("No test groundtruth directory '%s'" % test_root)
      assert isinstance(input_format, Format)
      assert isinstance(output_format, Format)
      steps = converter.get_steps(input_format.converter, output_format.converter)
      for filename in glob(join(input_dir, "*." + input_format.ext)):
         root_filename = splitext(split(filename)[1])[0]
         out_file = join(output_dir, root_filename + "." + output_format.ext)
         print "Converting '%s' to '%s'..." % (split(filename)[1], split(out_file)[1])
         sys.stdout.flush()
         converter.run_steps(steps, filename, filename=out_file, warnings=True, verbose=True)
         if callback:
            callback(filename, out_file)
         if groundtruth:
            gt_file = join(gt_dir, root_filename + "." + output_format.ext)
            if isfile(gt_file):
               test_list = open(out_file, "rU").readlines()
               gt_list = open(gt_file, "rU").readlines()
               for a, b in zip(test_list, gt_list):
                  if a.strip() != b.strip():
                     groundtruth_warnings.append(out_file)
                     break

   if len(groundtruth_warnings):
      print textwrap.fill("WARNING: The following files failed the groundtruth check:")
      print textwrap.fill(", ".join(groundtruth_warnings))
      
