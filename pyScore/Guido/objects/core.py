"""
Core GUIDO objects
Python GUIDO tools

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

from __future__ import generators

from pyScore.util.rational import Rat
from pyScore.Guido.parser.lexer import ParseError, Position
from pyScore.util.structures import SortedListSet

from inspect import isclass
import re
import sys
try:
    import textwrap
except ImportError:
    from pyScore.util.backport import textwrap
from types import *

class GuidoError(Exception):
    pass

class GUIDO_OBJECT(object):
    def __init__(self, pos=None):
        if not pos is None:
            assert isinstance(pos, Position)
        self.pos = pos
        self.tags = {}
        self.parent = None
        self.time_spine = Rat(0, 1)

    def write_guido(self, stream, state={}):
        stream.write("[ERROR! Undefined GUIDO object in stream.]")

    def visit_flat(self):
        yield self
        if hasattr(self, "collection"):
            for a in self.collection:
                for b in a.visit_flat():
                    yield b

    def visit_flat_with_chords(self):
        yield self
        if hasattr(self, "collection") and not isinstance(self, Chord):
            for a in self.collection:
                for b in a.visit_flat_with_chords():
                    yield b

    def visit_flat_chord_first_note(self):
        yield self
        if isinstance(self, Chord):
            if len(self.collection):
                yield self.collection[0]
        elif hasattr(self, "collection"):
            for a in self.collection:
                for b in a.visit_flat_chord_first_note():
                    yield b

    def calc_time_spines(self, start=Rat(0, 1)):
        time_spine = start
        for item in self.visit_flat_with_chords():
            if isinstance(item, Sequence):
                time_spine = start
            item.time_spine = time_spine
            # "Time stands still" within a Chord
            if isinstance(item, Chord):
                item.time_spine = time_spine
                notes = list(item.visit_flat())
                for a in notes[1:]:
                    a.time_spine = time_spine
            time_spine += item.get_duration()

    def get_tag(self, tag_name):
        return self.tags.get(tag_name, {})
           
    def raise_error(self, message):
        if self.pos == None:
            raise GuidoError("%s\n%s\n" % (repr(self), textwrap.fill(message)))
        raise ParseError(self.pos, message)

    def get_duration(self):
        return Rat(0, 1)

    def set_duration(self, num, den, dotting=0):
        pass
                
class COLLECTION(GUIDO_OBJECT):
    separator = ' '
    parens = '[]'
    
    def __init__(self, *args, **kwargs):
        GUIDO_OBJECT.__init__(self, *args, **kwargs)
        self.collection = []

    def __repr__(self):
        return "<" + self.__class__.__name__ + ": " + repr(self.collection) + ">"

    def append(self, item):
        self.collection.append(item)
        item.parent = self

class NULL_COLLECTION(COLLECTION):
    def append(self, item):
        pass

    def write_guido(self, stream, state={}):
        pass

class INLINE_COLLECTION(COLLECTION):
    def write_guido(self, stream, state={}):
        if len(self.collection):
            stream.write(self.parens[0])
            length = len(self.collection) - 1
            for i in xrange(len(self.collection)):
                self.collection[i].write_guido(stream, state)
                if i != length:
                    stream.write(self.separator)
            stream.write(self.parens[1])

class NONINLINE_COLLECTION(COLLECTION):
    def write_guido(self, stream, state={}):
        pass

class Score(INLINE_COLLECTION):
    parens = '  '

    def __init__(self, *args, **kwargs):
        INLINE_COLLECTION.__init__(self, *args, **kwargs)
        self._dict = dict

    def append(self, item):
        # We always have a top level Segment, even if it
        # contains only one part (Sequence)
        if len(self.collection):
            raise RuntimeError("A score may only have one top-level element.")
        if isinstance(item, Sequence):
            segment = Segment()
            segment.append(item)
            self.toplevel = segment
            self.collection = [self.toplevel]
        elif isinstance(item, Segment):
            self.toplevel = item
            self.collection = [self.toplevel]
        else:
            raise RuntimeError("A score can only have a Sequence or a Segment as the top-level element.")

    def write_guido(self, stream, state={}):
        self.toplevel.write_guido(stream, state)

########################################
# NOTES AND RESTS

class DURATIONAL(GUIDO_OBJECT):
    one_dot = Rat(3, 2)
    two_dots = Rat(7, 4)

    standard_durations = SortedListSet([2.0] + [1.0 / pow(2, x) for x in range(8)])
    one_dot_durations = SortedListSet([x * one_dot for x in standard_durations])
    two_dot_durations = SortedListSet([x * two_dots for x in standard_durations])
    
    def __init__(self, num, den=None, dotting=None, *args, **kwargs):
        GUIDO_OBJECT.__init__(self, *args, **kwargs)
        self.set_duration(num, den, dotting)

    def set_duration(self, num, den=None, dotting=None):
        if isinstance(num, Rat):
            self._num = num.num
            self._den = num.den
            self._dotting = 0
        else:
            if not num is None:
                self._set_num(num)
            else:
                self._num = 1
            if not den is None:
                self._set_den(den)
            else:
                self._den = 4
            if not dotting is None:
                self._set_dotting(dotting)
            else:
                self._dotting = 0
        self.normalize_duration()

    def normalize_duration(self):
        # The comparison is imperfect, but the generated result is
        dur = float(self._num) / float(self._den)
        if dur in self.one_dot_durations:
            new_dur = Rat(self._num, self._den) / self.one_dot
            self._num = new_dur.num
            self._den = new_dur.den
            self._dotting = 1
        elif dur in self.two_dot_durations:
            new_dur = Rat(self._num, self._den) / self.two_dots
            self._num = new_dur.num
            self._den = new_dur.den
            self._dotting = 1
        return

    def get_duration(self):
        if self._dotting == 0:
            return Rat(self._num, self._den)
        elif self._dotting == 1:
            return Rat(self._num * self.one_dot.num, self._den * self.one_dot.den)
        elif self._dotting == 2:
            return Rat(self._num * self.two_dots.num, self._den * self.two_dots.den)
        self.raise_error("Too many dots.")

    def __repr__(self):
        return "*%d/%d%s" % (self.num, self.den, '.' * self.dotting)

    def write_guido(self, stream, state={}):
        if state['last_duration'] != (self.num, self.den, self.dotting):
            if (self.num != 1):
                stream.write("*")
                stream.write(str(self.num))
            stream.write("/")
            stream.write(str(self.den))
            stream.write("." * self.dotting)
        state['last_duration'] = (self.num, self.den, self.dotting)

    def _get_num(self):
        return self._num
    def _set_num(self, num):
        self._num = num
    num = property(_get_num, _set_num)

    def _get_den(self):
        return self._den
    def _set_den(self, den):
        self._den = den
    den = property(_get_den, _set_den)
        
    def _get_dotting(self):
        return self._dotting
    def _set_dotting(self, dotting):
        if type(dotting) == type(''):
            dotting = len(dotting)
        if type(dotting) != type(0) or dotting < 0 or dotting > 2:
            self.raise_error(
                "'%s' is not a valid dotting.  Legal values are '', '.', '..', 0, 1, or 2." %
                str(dotting))
        self._dotting = dotting
    dotting = property(_get_dotting, _set_dotting)

class PITCHED(GUIDO_OBJECT):
    solfege_pitch_names = 'do re mi me fa sol la ti si h'.split()
    normal_pitch_names = list("abcedfg")
    pitch_names = solfege_pitch_names + normal_pitch_names
    pitch_names_to_semitones = {'c': 0, 'd': 2, 'e': 4, 'f': 5, 'g': 7,
                                'a': 9, 'b': 11, 'do': 0, 're': 2,
                                'mi': 4, 'me': 4, 'fa': 5, 'sol': 7, 'la': 9,
                                'ti': 11, 'si': 11, 'h': 11}
    pitch_names_to_normal_pitch_names = {
        'h': 'b', 'do': 'c', 're': 'd', 'mi': 'e', 'me': 'e', 'fa': 'f', 'sol': 'g',
        'la': 'a', 'ti': 'b', 'si': 'b' }
    for name in normal_pitch_names:
        pitch_names_to_normal_pitch_names[name] = name
    
    accidentals = ['&&', '&', '#', '##', 'is', '']
    accidentals_to_semitones = {'&&': -2, '&': -1, '#': 1, 'is': 1,
                                '##': 2, '': 0}

    def __init__(self, pitch_name=None, octave=None, accidental=None,
                 *args, **kwargs):
        GUIDO_OBJECT.__init__(self, *args, **kwargs)
        self._pitch_name = 'c'
        self._octave = 1
        self._accidental = ''
        self._volume = 0.5

        if not pitch_name is None:
            self._set_pitch_name(pitch_name)
        if not octave is None:
            self._set_octave(octave)
        if not accidental is None:
            self._set_accidental(accidental)

    def __repr__(self):
        return "%s%s%d" % (self.pitch_name, self.accidental, self.octave)

    def write_guido(self, stream, state):
        stream.write(self.pitch_name)
        stream.write(self.accidental)
        if state['last_octave'] != self.octave:
            stream.write(str(self.octave))
        state['last_octave'] = self.octave

    def _get_pitch_name(self):
        return self._pitch_name
    def _set_pitch_name(self, name):
        if not name in self.pitch_names:
            self.raise_error(
                "'%s' is not a valid pitch name.  Legal values are %s." %
                (str(name), ", ".join([repr(x) for x in self.pitch_names])))
        self._pitch_name = name
    pitch_name = property(_get_pitch_name, _set_pitch_name)

    def _get_accidental(self):
        return self._accidental
    def _set_accidental(self, accidental):
        if not accidental in self.accidentals:
            self.raise_error(
                "'%s' is not a valid accidental.  Legal values are %s." %
                (str(accidental), ", ".join([repr(x) for x in self.accidentals])))
        self._accidental = accidental
    accidental = property(_get_accidental, _set_accidental)

    def _get_octave(self):
        return self._octave
    def _set_octave(self, octave):
        if type(octave) != type(0) or octave < -4 or octave > 6:
            self.raise_error(
                "'%s' is not a valid octave.  Legal values are in range [-4, 6]." %
                str(octave))
        self._octave = octave
    octave = property(_get_octave, _set_octave)

    def _get_volume(self):
        return self._volume
    def _set_volume(self, val):
        if type(val) != type(0.0) or val < 0 or val > 1.0:
            self.raise_error(
                "'%s' is not a valid volume level.  Legal values are in range [0,1]." %
                str(val))
        self._volume = val
    volume = property(_get_volume, _set_volume)

    def get_absolute_pitch(self):
        return (self.pitch_names_to_semitones[self._pitch_name] +
                self.accidentals_to_semitones[self._accidental] +
                (12 * (self._octave)))

class EVENT(GUIDO_OBJECT):
    pass

class Rest(EVENT, DURATIONAL):
    def __init__(self, num, den=None, dotting=0, *args, **kwargs):
        DURATIONAL.__init__(self, num, den, dotting, *args, **kwargs)

    def __repr__(self):
        return ("<Rest %s>" %
                (DURATIONAL.__repr__(self)))

    def write_guido(self, stream, state={}):
        stream.write("_")
        DURATIONAL.write_guido(self, stream, state)

class Empty(EVENT, DURATIONAL):
    def __init__(self, num, den=None, dotting=0, *args, **kwargs):
        DURATIONAL.__init__(self, num, den, dotting, *args, **kwargs)

    def __repr__(self):
        return ("<Empty %s>" %
                (DURATIONAL.__repr__(self)))

    def write_guido(self, stream, state={}):
        stream.write("empty")
        DURATIONAL.write_guido(self, stream, state)

class Note(EVENT, PITCHED, DURATIONAL):
    def __init__(self, pitch_name, octave, accidental,
                 num, den=None, dotting=None, *args, **kwargs):
        PITCHED.__init__(self, pitch_name, octave, accidental, *args, **kwargs)
        DURATIONAL.__init__(self, num, den, dotting, *args, **kwargs)

    def __repr__(self):
        return ("<Note %s%s>" %
                (PITCHED.__repr__(self), DURATIONAL.__repr__(self)))

    def write_guido(self, stream, state={}):
        PITCHED.write_guido(self, stream, state)
        DURATIONAL.write_guido(self, stream, state)


########################################
# TAGS

class TAG(GUIDO_OBJECT):
    default = 0
    parens = '()'
    separator = ' '
    
    def __init__(self, name_, id_, args_list, args_dict, *args, **kwargs):
        self.name = name_
        self.id = id_
        self.mode = ""
        self.use_parens = False
        self.starts_group = 0
        self.args_list = list(args_list)
        self.args_dict = args_dict
        self.events = []
        self.end_tag = None
        GUIDO_OBJECT.__init__(self, *args, **kwargs)

    def __repr__(self):
        items = (['"%s"' % x for x in self.args_list] +
                 ['%s="%s"' % (key, val)
                  for key, val in self.args_dict.items() if val != None])
        if len(items):
            args = "<%s>" % ", ".join(items)
        else:
            args = ""
        return "<Tag \\%s%s%s >" % (self.name, self.mode, args)

    def _get_full_name(self):
        return "%s:%s" % (self.name, self.id)
    full_name = property(_get_full_name)

    def escape(self, s):
        return s.replace('"', r'\"')

    def write_guido(self, stream, state={}):
        if self.mode == "End" and self.use_parens and self.events == []:
            stream.write(")")
            return
        stream.write("\\")
        stream.write(self.name)
        if not self.use_parens:
            stream.write(self.mode)
        if self.id != None:
            stream.write(":")
            stream.write(str(self.id))
        items = (['"%s"' % self.escape(x) for x in self.args_list] +
                 ['%s="%s"' % (key, self.escape(val))
                  for key, val in self.args_dict.items() if val != None])
        if len(items):
            stream.write("<")
            length = len(items) - 1
            stream.write(", ".join(items))
            stream.write(">")
        if self.use_parens:
            stream.write("(")

    def tag(self, item):
        item.tags.setdefault(self.__class__.__name__, []).append(self)
        self.events.append(item)

    def is_first(self, note):
        for n in self.events:
            if isinstance(n, (Note, Chord)):
                if isinstance(n, Note):
                    if n is note:
                        return True
                elif isinstance(n, Chord):
                    if note in n.collection:
                        return True
                return False
        return False
                            
    def is_last(self, note):
        for i in range(len(self.events)-1, -1, -1):
            n = self.events[i]
            if isinstance(n, (Note, Chord)):
                if isinstance(n, Note):
                    if n is note:
                        return True
                elif isinstance(n, Chord):
                    if note in n.collection:
                        return True
                break
        for i in range(len(self.events)-1, -1, -1):
            n = self.events[i]
            if isinstance(n, Chord):
                if note in n.collection:
                    return True
                break
        return False

class DEFAULT_TAG(TAG):
    pass
    
########################################
# Concrete collections

class Sequence(INLINE_COLLECTION):
    parens = ('[', ']\n')

    def __init__(self, pos=None):
        INLINE_COLLECTION.__init__(self, pos)

    def write_guido(self, stream, state={}):
        state['last_octave'] = None
        state['last_duration'] = None
        INLINE_COLLECTION.write_guido(self, stream, state)

class Segment(INLINE_COLLECTION):
    separator = ", "
    parens = "{}"

    def __init__(self, pos=None):
        INLINE_COLLECTION.__init__(self, pos)

class Chord(INLINE_COLLECTION, DURATIONAL):
    separator = ", "
    parens = "{}"

    def get_duration(self):
        m = Rat(0, 1)
        for note in self.collection:
            m = max(m, note.get_duration())
        return m

    def append(self, item):
        self.collection.append(item)
        item.parent = self.parent

class Barline(GUIDO_OBJECT):
    measure = None
    
    def __repr__(self):
        return "<Barline>"

    def write_guido(self, stream, state):
        stream.write("|\n")


########################################
# FACTORY FUNCTIONS

class Factory(object):
    pass

class EventFactoryClass(Factory):
    _pitch_names = PITCHED.solfege_pitch_names + ["empty"]
    _rer_pitch_name = ("(?P<pitch_name>%s|[a-g_])" %
                      "|".join([u"(?:%s)" % x for x in _pitch_names]))
    _rer_octave1 = "(?P<octave1>[+\-]?[0-9]+)?"
    _rer_accidental = "(?P<accidental>(?:is)|#+|&+)?"
    _rer_octave2 = "(?P<octave2>[+\-]?[0-9]+)?"
    _rer_num = "(?:\*(?P<num>[0-9]+))?"
    _rer_den = "(?:/(?P<den>[0-9]+))?"
    _rer_dotting = "(?P<dotting>\.*)"
    _rer_duration = _rer_num + _rer_den + _rer_dotting
    regex = re.compile(
        _rer_pitch_name +
        _rer_octave1 +
        _rer_accidental +
        _rer_octave2 +
        _rer_duration)

    note_class = Note
    rest_class = Rest
    empty_class = Empty

    def __init__(self, module):
        self._module = module

    def __call__(self, pitch_name, octave=None, accidental=None,
                 num=None, den=None, dotting=None, pos=None):
        if pitch_name == "_":
            return self._module['Rest'](num, den, dotting, pos=pos)
        if pitch_name == "empty":
            return self._module['Empty'](num, den, dotting, pos=pos)
        if pitch_name in PITCHED.pitch_names:
            return self._module['Note'](pitch_name, octave, accidental,
                                        num, den, dotting, pos=pos)
        else:
            match = self.regex.match(pitch_name)
            if match != None:
                matches = match.groupdict()
                return self.__call__(matches['pitch_name'], matches['octave'],
                                     matches['accidental'], matches['num'],
                                     matches['den'], matches['dotting'],
                                     pos=pos)
            else:
                raise ValueError("'%s' is not a valid GUIDO pitch name, note or rest." %
                                 pitch_name)
EventFactory = EventFactoryClass(globals())

class TagFactoryClass(Factory):
    regex_tag_name = re.compile("[A-Za-z_][A-Za-z0-9_]*")
    regex_arg_str = '(?P<arg>(?:(?P<key>[A-Za-z_][A-Za-z0-9_]*)=)?(?:")?(?P<value>[^"]*)(?:")?)'
    regex_arg = re.compile(regex_arg_str)
    regex = re.compile(
        r'\\(?P<name>[A-Za-z_][A-Za-z0-9_]*)(:(?P<id>[0-9]+))?(?:\<(?P<args>[^>]*)\>)?'
    )
    
    def __init__(self, tags):
        if type(tags) not in (ListType, TupleType):
            tags = [tags]
        self._registered_tags = {}
        for t in tags:
            self.register_module_of_tags(t)
        
    def register_module_of_tags(self, t):
        if not type(t) == DictType:
            t = t.__dict__
        for key, val in t.items():
            if (isclass(val) and
                issubclass(val, TAG)):
                self._registered_tags[key] = val

    def __call__(self, name, id, args, pos=None):
        if (not type(name) in (StringType, UnicodeType) or len(name) < 1 or
            self.regex_tag_name.match(name) is None):
            raise ValueError("'%s' is an invalid tag name." % str(name))

        if name.startswith('\\'):
            match = regex.match(name)
            if not match is None:
                matches = match.groupdict()
                return self.__call__(
                    matches['name'], matches['id'], matches['args'],
                    pos=pos)
            else:
                raise ValueError("'%s' is not a valid tag." % name)
            
        if id != None:
            try:
                id = int(id)
            except:
                raise ValueError("'%s' is an invalid tag id number." % id)

        args_list = []
        args_dict = {}
        if type(args) in (type(()), type([])):
            args_list = args
        elif type(args) in (StringType, UnicodeType):
            first = True
            while len(args):
                if not first:
                    if args.startswith(","):
                        args = args[1:].strip()
                    else:
                        raise ValueError("Couldn't parse arguments to tag '%s'" % name)
                first = False
                match = self.regex_arg.match(args)
                if match == None:
                    raise ValueError("'%s' is an invalid argument to tag '%s'." %
                                     (arg, name))
                match_dict = match.groupdict()
                if match_dict['key'] != None:
                    args_dict[match_dict['key']] = match_dict['value']
                else:
                    args_list.append(match_dict['value'])
                args = args[match.end("arg"):].strip()
        elif type(args) == type({}):
            args_dict = args

        mode = ""
        if self._registered_tags.has_key(name):
            tag_cls = self._registered_tags[name]
        else:
            if name.endswith("Begin"):
                name = name[:-5]
                mode = "Begin"
            elif name.endswith("End"):
                name = name[:-3]
                mode = "End"
            if self._registered_tags.has_key(name):
                tag_cls = self._registered_tags[name]
            else:
                tag_cls = self._registered_tags['DEFAULT_TAG']
        tag = tag_cls(name, id, args_list, args_dict, pos=pos)
        tag.mode = mode
        return tag

TagFactory = TagFactoryClass(globals())
