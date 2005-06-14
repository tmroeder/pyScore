"""
Code that builds convertors between different types
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

from inspect import getargspec
import sys

def dummy_function(percent):
   pass

class ConverterGraph:
   def __init__(self, modules):
      self.inputs = {}
      self.outputs = []
      for module in modules:
         if not hasattr(module, "inputs") or not hasattr(module, "outputs"):
            raise ValueError("module '%s' does not appear to be a convertor module." % module)
         for input in module.inputs:
            self.inputs[input] = {}
         for output in module.outputs:
            self.outputs.append(output)
      converters = {}
      for input in self.inputs.keys():
         for output in self.outputs:
            for module in modules:
               converter_name = "%s_to_%s" % (input, output)
               if hasattr(module, converter_name):
                  converter = getattr(module, converter_name)
                  if not converters.has_key(converter) and self.inputs[input].has_key(output):
                     raise ValueError(
                        "Multiple direct routes from '%s' to '%s'." % (input, output))
                  converters[converter] = None
                  self.inputs[input][output] = getattr(module, converter_name)

   def _get_steps(self, input, output, tried=[]):
      if self.inputs[input].has_key(output):
         return [(self.inputs[input][output], input, output)]
      options = []
      for key, val in self.inputs[input].items():
         if key not in tried and self.inputs.has_key(key):
            option = self._get_steps(key, output, tried + [input])
            if len(option) and option[-1][-1] == output:
               options.append([(val, input, key)] + option)
      if len(options):
         options.sort(lambda x, y: cmp(len(x), len(y)))
         return options[0]
      return []

   def get_steps(self, input, output):
      if self.inputs.has_key(input) and output in self.outputs:
         steps = self._get_steps(input, output)
         if len(steps):
            return steps
      raise ValueError(
         "There is no way to convert '%s' to '%s'." % (input, output))

   def run_steps(self, steps, input, progress_callback=dummy_function, **kwargs):
      for i, (step, a, b) in enumerate(steps):
         new_dict = {}
         for key in getargspec(step)[0]:
            if kwargs.has_key(key):
               new_dict[key] = kwargs[key]
         input = step(input, **new_dict)
         progress_callback(float(i) / float(len(steps) - 1))
      return input

   def make_dot_file(self, file):
      file.write("digraph g {\n")
      nodes = {}
      for input in self.inputs.keys():
         nodes[input] = None
      for output in self.outputs:
         nodes[output] = None
      for node in nodes:
         if node.endswith("file"):
            file.write('"%s" [style=filled, fillcolor=LightBlue];\n' % node.replace("_", " "))
      for input, val in self.inputs.items():
         for output in val.keys():
            file.write('"%s" -> "%s";\n' % (input.replace("_", " "), output.replace("_", " ")))
      file.write("}\n")

def convert(modules, input_format, output_format, input, stream=sys.stdout, progress_callback=dummy_function, **kwargs):
   converter = ConverterGraph(modules)
   steps = converter.get_steps(input_format, output_format)
   return converter.run_steps(steps, input, stream=stream, progress_callback=progress_callback, **kwargs)

__all__ = "ConverterGraph convert".split()
