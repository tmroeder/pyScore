"""
Helpers for the scripts
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
from pyScore.Guido import noteserver
from pyScore.util.console import *

from time import strftime
from os.path import splitext, split, join, exists, isdir, isfile
import os
import sys
import traceback
from urllib import urlencode

class ConverterOptions:
   def __init__(self, input_format, output_format, extra_args=None, description=None):
      pretty_from = "%s (.%s)" % (input_format.name, input_format.ext),
      pretty_to = "%s (.%s)" % (output_format.name, output_format.ext),

      if description == None:
         description = "Converts %s to %s" % (pretty_from, pretty_to)
      parser = OptionParser(description + "\nusage: \%prog [-o=output_file] [-w] [-v] [-t] input_file")

      parser.add_option("-o", "--output", dest="output",
                        help="Output file in %s format" % output_format)
      parser.add_option("-w", "--warnings", action="store_true", dest="warnings",
                        help="Display warnings")
      parser.add_option("-v", "--verbose", action="store_true", dest="verbose",
                        help="Verbose feedback")
      parser.add_option("-t", "--trace", action="store_true", dest="trace",
                        help="Trace the actions of the parser")
      parser.add_option("-g", "--gzip", action="store_true", dest="gzip",
                        help="Save the result in gzip compressed form")
      parser.add_option("-b", "--bzip2", action="store_true", dest="bzip2",
                        help="Save the result in bzip2 compressed form")
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

      if options.gzip and options.bzip:
         parser.error("Can only specify one of --gzip or --bzip2.")
      if options.gzip:
         output_format.ext += ".gz"
         if not self.output_file.endswith(".gz"):
            self.output_file += ".gz"
      elif options.bzip2:
         output_format.ext += ".bz2"
         if not self.output_file.endswith(".bz2"):
            self.output_file += ".bz2"
      self.options = options

   def __getattr__(self, attr):
      return getattr(self.options, attr)

class Format:
   def __init__(self, name, ext, converter):
      self.name = name
      self.ext = ext
      self.converter = converter

def convert(modules, input_format, output_format,
            extra_args=None, callback=None, extra_dict=[]):
   from pyScore.convert import ConverterGraph
   assert isinstance(input_format, Format)
   assert isinstance(output_format, Format)
   options = ConverterOptions(input_format, output_format, extra_args=extra_args)

   converter = ConverterGraph(modules)
   steps = converter.get_steps(input_format.converter, output_format.converter)

   for filename in options.input_files:
      if options.output_file:
         output = options.output_file
      else:
         output = splitext(filename)[0] + "." + output_format.ext
      print "Converting '%s' to '%s'..." % (split(filename)[1], split(output)[1])
      sys.stdout.flush()
      extras = {}
      for x in extra_dict:
         extras[x] = getattr(options, x)
      converter.run_steps(
         steps, filename, filename=output, progress_callback=progress_callback,
         warnings=options.warnings, verbose=options.verbose, **extras)
      if callback:
         callback(options, filename, output)
      print

def _get_test_directories(test_dir, dir, groundtruth):
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
   gt_dir = join(root_dir, "groundtruth")
   if groundtruth and not isdir(gt_dir):
      raise IOError("No test groundtruth directory '%s'" % test_root)
   return root_dir, input_dir, output_dir, gt_dir

def document_lines(stream, filename, lines):
   stream.write("\n")
   stream.write(split(filename)[1])
   stream.write("::\n\n")
   for line in lines:
      stream.write(textwrap.fill(line, initial_indent="  ", subsequent_indent="  "))
      stream.write("\n")
   stream.write("\n\n")

def document_file(stream, filename):
   document_lines(stream, filename, open(filename, "rU").readlines())
   if filename.endswith("gmn"):
      url = noteserver.get_url(open(filename, "rU").read())
      stream.write(".. image:: %s\n\n" % url)

def compare_files(out_file, gt_file):
   test_list = open(out_file, "rU").readlines()
   gt_list = open(gt_file, "rU").readlines()
   comments = ("%", "<!")
   i = 0
   j = 0
   while i < len(test_list) and j < len(gt_list):
      a = test_list[i]
      b = gt_list[j]
      for comment in comments:
         if a.startswith(comment):
            i += 1
         if b.startswith(comment):
            j += 1
      if i < len(test_list) and j < len(gt_list):
         a = test_list[i]
         b = gt_list[j]
         if a.strip() != b.strip():
            return False
      i += 1
      j += 1
   return True

def test(modules, test_dir, tests, groundtruth=False, callback=None):
   parser = OptionParser("\nusage: \%prog [--doc=documentation_dir] test_directory")
   
   parser.add_option("-d", "--doc", dest="doc",
                     help="An optional documentation directory to generate documentation of this test")
   (options, args) = parser.parse_args()

   if len(args):
      if isdir(args[0]):
         test_dir = args[0]
   if not isdir(test_dir):
      print "Test directory '%s' can not be found." % test_dir
      sys.exit(1)

   make_documentation = False
   if options.doc != None:
      make_documentation = True
      doc_dir = options.doc
      if not isdir(doc_dir):
         print "Documentation directory '%s' does not exist." % doc_dir
      doc_fd = open(join(doc_dir, "tests.txt"), "wU")
      doc_fd.write("Test results\n============\n\nTest results generated at %s\n\n" %
                   strftime("%H:%M %Z on %A, %B %d, %Y"))
      doc_fd.write("- (E): test caused an exception\n- (G): test does not match groundtruth\n- (U): no groundtruth provided\n\n")
      doc_fd.write(".. contents::\n\n")

   from pyScore.convert import ConverterGraph
   converter = ConverterGraph(modules)
   groundtruth_failures = []
   groundtruth_not_available = []
   errors = []
   for dir, input_format, output_format, title, description in tests:
      root_dir, input_dir, output_dir, gt_dir = _get_test_directories(test_dir, dir, groundtruth)
      assert isinstance(input_format, Format)
      assert isinstance(output_format, Format)
      steps = converter.get_steps(input_format.converter, output_format.converter)
      
      if make_documentation:
         doc_fd.write(title)
         doc_fd.write("\n")
         doc_fd.write("-" * len(title))
         doc_fd.write("\n\n")
         doc_fd.write(description)
         doc_fd.write("\n\n")
      files = glob(join(input_dir, "*." + input_format.ext))
      files.sort()
      for filename in files:
         root_filename = splitext(split(filename)[1])[0]
         documentation_header = root_filename
         out_file = join(output_dir, root_filename + "." + output_format.ext)
         print "Converting '%s' to '%s'..." % (split(filename)[1], split(out_file)[1])
         sys.stdout.flush()
         try:
            converter.run_steps(steps, filename, filename=out_file, progress_callback=progress_callback,
                                warnings=True, verbose=True)
         except Exception, e:
            errors.append("Exception from '%s':\n\n" % filename)
            errors.extend(traceback.format_exception(*sys.exc_info()))
            errors.append("\n")
            documentation_header += " (E)"
         else:
            if callback:
               callback(filename, out_file)
            if groundtruth:
               gt_file = join(gt_dir, root_filename + "." + output_format.ext)
               if isfile(gt_file):
                  if not compare_files(out_file, gt_file):
                        groundtruth_failures.append(out_file)
                        documentation_header += " (G)"
               else:
                  groundtruth_not_available.append(out_file)
                  documentation_header += " (U)"
         if make_documentation:
            doc_fd.write(documentation_header)
            doc_fd.write("\n")
            doc_fd.write("'" * len(documentation_header))
            document_file(doc_fd, filename)
            if documentation_header.find("(E)") == -1:
               document_file(doc_fd, out_file)
         print
   if len(errors):
      print textwrap.fill("ERROR: The following files caused exceptions during conversion:")
      print "".join(errors)
   if len(groundtruth_not_available):
      print textwrap.fill("WARNING: The following files do not have groundtruth available:")
      print textwrap.fill(", ".join(groundtruth_not_available))
   if len(groundtruth_failures):
      print textwrap.fill("WARNING: The following files failed the groundtruth check:")
      print textwrap.fill(", ".join(groundtruth_failures))
      
