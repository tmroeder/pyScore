"""
Some source management tools

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

from cStringIO import StringIO
from glob import glob
from os.path import join, walk, split

def get_notes(directory, note_types = (("NOTE", "Notes"),
                                       ("EXT", "Bugs or shortcomings in other systems"),
                                       ("TODO", "To-dos"),
                                       ("PLAN", "Longer-term plans")),
              file_types = ("py", "cpp"), comment_types = ("#", r"//", "%")):
   notes = {}
   def visit(arg, dir, names):
      for ext in file_types:
         for file in glob(join(dir, "*." + ext)):
            current_note = None
            for line in open(file, "r").readlines():
               line = line.strip()
               for comment in comment_types:
                  if line.startswith(comment):
                     line = line[len(comment):].strip()
                     if current_note == None:
                        for key, val in note_types:
                           if line.startswith(key):
                              current_note = line[len(key)+1:].strip()
                              notes.setdefault(key, []).append((file, current_note))
                     else:
                        current_note += " " + line
                  else:
                     current_note = None
   walk(directory, visit, ())

   text = StringIO()
   for category, name in note_types:
      text.write(name)
      text.write("\n")
      text.write('-' * len(name))
      text.write("\n\n")
      for file, note in notes[category]:
         if note.strip() != "":
            text.write("- ")
            text.write(note)
            text.write(" [%s]" % split(file)[1])
            text.write("\n\n")
   return text.getvalue()
