"""
Helpers for the scripts

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

from pyScore.config import config
from pyScore.convert import ConverterGraph
from pyScore.elementtree.ElementTree import parse, tostring
from pyScore.Guido import noteserver
from pyScore.util.console import *

try:
   import textwrap
except ImportError:
   from pyScore.util.backport import textwrap

from glob import glob
from time import strftime
from os.path import splitext, split, join, exists, isdir, isfile
import os
import sys
import traceback
from urllib import urlencode

class Format:
   def __init__(self, name, ext, converter):
      self.name = name
      self.ext = ext
      self.converter = converter

class convert:
   def __init__(self, modules, input_format, output_format, pre_callback=None, post_callback=None):
      assert isinstance(input_format, Format)
      assert isinstance(output_format, Format)

      config.add_option("-o", "--output", action="store", help="Output file")
      config.add_option("", "--gzip", action="store_true", help="Save output as gzip compressed file")
      config.add_option("", "--bzip2", action="store_true", help="Save output as bzip2 compressed file")

      options = self.get_options(input_format, output_format)

      converter = ConverterGraph(modules)
      steps = converter.get_steps(input_format.converter, output_format.converter)

      for filename in self.input_files:
         if self.output_file:
            output = self.output_file
         else:
            output = splitext(filename)[0] + "." + output_format.ext
         print "Converting '%s' to '%s'..." % (split(filename)[1], split(output)[1])
         sys.stdout.flush()
         if pre_callback:
            pre_callback(options, filename, output)
         converter.run_steps(
            steps, filename, filename=output, progress_callback=progress_callback)
         if post_callback:
            post_callback(options, filename, output)
         print

   def get_options(self, input_format, output_format):
      pretty_from = "%s (.%s)" % (input_format.name, input_format.ext)
      pretty_to = "%s (.%s)" % (output_format.name, output_format.ext)

      config.usage = "\nConvert from %s to %s\n" % (pretty_from, pretty_to)
      config.usage += "usage: %prog [options] input_file"
      (options, args) = config.parse_args()

      if len(args) < 1:
         config.error("No input file(s) specified")
      self.input_files = []
      for arg in args:
         self.input_files.extend(glob(arg))
      if not len(self.input_files):
         config.error("Cannot find input file(s) '%s'" % " ".join(args))
      if options.output != "":
         if len(self.input_files) != 1:
            config.error("Cannot specify an output file when converting multiple files.")
         self.output_file = options.output

      if options.gzip and options.bzip:
         config.error("Can only specify one of --gzip or --bzip2.")
      if options.gzip:
         output_format.ext += ".gz"
         if not self.output_file.endswith(".gz"):
            self.output_file += ".gz"
      elif options.bzip2:
         output_format.ext += ".bz2"
         if not self.output_file.endswith(".bz2"):
            self.output_file += ".bz2"
      return options

class test:
   def __init__(self, modules, test_dir, tests, groundtruth=False, callback=None):
      config.add_option("", "--doc", action="store", help="Output directory")
      config.usage = "\nusage: \%prog [options] [test_directory]"
      (options, args) = config.parse_args()

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
         self.doc_fd = open(join(doc_dir, "tests.txt"), "wU")
         self.doc_header()

      converter = ConverterGraph(modules)
      groundtruth_failures = []
      groundtruth_not_available = []
      errors = []
      for dir, input_format, output_format, title, description in tests:
         root_dir, input_dir, output_dir, gt_dir = self.get_test_directories(test_dir, dir, groundtruth)
         assert isinstance(input_format, Format)
         assert isinstance(output_format, Format)
         steps = converter.get_steps(input_format.converter, output_format.converter)

         if make_documentation:
            self.doc_section(title, description)
         files = glob(join(input_dir, "*." + input_format.ext))
         files.sort()
         for filename in files:
            root_filename = splitext(split(filename)[1])[0]
            documentation_header = root_filename
            out_file = join(output_dir, root_filename + "." + output_format.ext)
            print "Converting '%s' to '%s'..." % (split(filename)[1], split(out_file)[1])
            sys.stdout.flush()
            try:
               converter.run_steps(steps, filename, filename=out_file, progress_callback=progress_callback)
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
                     if not self.compare_files(out_file, gt_file):
                        groundtruth_failures.append(out_file)
                        documentation_header += " (G)"
                  else:
                     groundtruth_not_available.append(out_file)
                     documentation_header += " (U)"
            if make_documentation:
               self.doc_result(documentation_header, filename, out_file)
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

   def get_test_directories(self, test_dir, dir, groundtruth):
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

   def doc_header(self):
      self.doc_fd.write("Test results\n============\n\nTest results generated at %s\n\n" %
                   strftime("%H:%M %Z on %A, %B %d, %Y"))
      self.doc_fd.write("- (E): test caused an exception\n- (G): test does not match groundtruth\n- (U): no groundtruth provided\n\n")
      self.doc_fd.write(".. contents::\n\n")

   def doc_section(self, title, description):
      doc_fd = self.doc_fd
      doc_fd.write(title)
      doc_fd.write("\n")
      doc_fd.write("-" * len(title))
      doc_fd.write("\n\n")
      doc_fd.write(description)
      doc_fd.write("\n\n")

   def doc_result(self, documentation_header, filename, out_file):
      doc_fd = self.doc_fd
      doc_fd.write(documentation_header)
      doc_fd.write("\n")
      doc_fd.write("'" * len(documentation_header))
      doc_fd.write("\n\n")
      self.doc_file(doc_fd, filename)
      if documentation_header.find("(E)") == -1:
         self.doc_file(doc_fd, out_file)
         
   def doc_file(self, stream, filename):
      if filename.endswith("gmn"):
         self.doc_lines(stream, filename, open(filename, "rU").readlines())
         url = noteserver.get_url(open(filename, "rU").read())
         stream.write("`See image`__\n\n.. __: %s\n\n" % url)
      elif filename.endswith("xml"):
         stream.write("`See XML`__\n\n.. __: ./%s\n\n" % filename.replace("\\", "/"))
      elif filename.endswith("mid"):
         stream.write("`Hear MIDI`__\n\n.. __: ./%s\n\n" % filename.replace("\\", "/"))

   def doc_lines(self, stream, filename, lines):
      stream.write(split(filename)[1])
      stream.write("::\n\n")
      for line in lines:
         stream.write(textwrap.fill(line, initial_indent="  ", subsequent_indent="  "))
         stream.write("\n")
      stream.write("\n\n")

   def compare_files(self, out_file, gt_file):
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
      
__all__ = "test convert Format".split()
