"""
GUIDO Parser
Builds a data structure of GUIDO objects

The GUIDO parser is built upon a very basic general recursive-
-descent parser library implemented in lexer.py

Python GUIDO tools

Copyright (C) 2004 Michael Droettboom

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
 
You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
"""

from __future__ import generators
from lexer import Token, Tokenizer, WrongToken
from pyScore.Guido.objects import core
from pyScore.Guido.tree_builder import GuidoTreeBuilder
try:
    import textwrap
except ImportError:
    from pyScore.util.backport import textwrap

from copy import copy
import re
import sys
from types import StringType, UnicodeType

########################################
# TOKENS

class GuidoTokenizer(Tokenizer):
    """This defines the tokens in the GUIDO language.  Since regular
    expressions are used for the matching, complex constructs such as
    the notes and tags can be treated as single 'tokens' with internal
    subparts.
    """
    
    class Note(Token):
        """The note token is defined in the GUIDO object core.py."""
        regex = core.EventFactory.regex

    class Tag(Token):
        """The tag token is defined in the GUIDO object core.py."""
        regex = core.TagFactory.regex

    class SequenceStart(Token):
        regex = re.compile("\[")

    class SequenceEnd(Token):
        regex = re.compile("\]")

    class SegmentStart(Token):
        regex = re.compile("\{")

    class SegmentEnd(Token):
        regex = re.compile("\}")

    ChordStart = SegmentStart
    ChordEnd = SegmentEnd

    class GroupingStart(Token):
        """This should match '(', but not '(*' which starts a comment."""
        regex = re.compile("\((?:(?!\*))")

    class GroupingEnd(Token):
        regex = re.compile(r"\)")

    class Comma(Token):
        regex = re.compile(",")

    class Barline(Token):
        regex = re.compile(r"\|")

    class SingleLineComment(Token):
        regex = re.compile("%(?P<comment>[^\n]*)")

    class MultiLineComment(Token):
        regex = re.compile("\(\*.*\*\)")

    # tokens lists all the tokens in the language
    tokens = (Barline, Note, Tag, SequenceStart, SequenceEnd,
              SegmentStart, SegmentEnd, GroupingStart,
              GroupingEnd, Comma)

    # filtered_tokens are tokens that will be
    # ignored and can appear anywhere, such as comments
    # and whitespace
    filtered_tokens = (
        list(Tokenizer.filtered_tokens) +
        [SingleLineComment, MultiLineComment])

########################################
# PARSING

class GuidoParser:
    """This is a recursive-descent parser for the GUIDO language.
    It parses a string and returns a tree of GUIDO objects
    (defined in guido_objects/core.py).  The top of this tree is
    always a Parts object.

    This is a clean room implementation based on the GUIDO grammar
    specified in leanGUIDO."""

    # default note defines the default attributes of notes
    # (for notes that begin a part that have unspecified
    # attributes.)
    default_note = {'pitch_name': 'c',
                    'octave1': 1,
                    'accidental': '',
                    'octave2': 1,
                    'num': 1,
                    'den': 4,
                    'dotting': ''}

    def __init__(self, tags, warnings=True, trace=False):
        """
        tags: dictionaries containing tags
        warnings: if true, print out warning messages        
        """
        # self.s = s
        self._tag_factory = core.TagFactoryClass(tags)
        self._warnings = warnings
        if trace:
            self.trace = self._trace_real
        else:
            self.trace = self._trace_dummy

    def _trace_real(self, name, tokens):
        position = tokens.current_position
        s = tokens.s[position.pos:min(len(tokens.s), position.pos + 20)]
        s = s.replace("\n", "")
        s = s.replace("\l", "")
        print name + " " * (20 - len(name)) + ": " + s

    def _trace_dummy(self, name, tokens):
        pass

    def parse(self, s):
        """Parse a given GUIDO string, returning a tree of GUIDO objects.
        The top of this tree is always a Parts object.
        """
        assert type(s) in (StringType, UnicodeType)
        self.s = s
        self.unknown_tags = {}
        self.active_tags = []
        tokens = GuidoTokenizer(self.s)
        builder = GuidoTreeBuilder(self._tag_factory)
        tokens = self.top(tokens, builder)
        if self._warnings:
            if not tokens.at_end():
                sys.stderr.write("WARNING: Extra text at end of file\n")
            if len(self.unknown_tags.keys()):
                sys.stderr.write("WARNING: Unknown tags:\n")
                sys.stderr.write(textwrap.fill(', '.join(['\\' + x for x in self.unknown_tags.keys()])))
                sys.stderr.write("\n")
        return builder.score

    def FILE(self, tokens, builder):
        """The top-level parsing node.  Initializes state and begins parsing
        a GUIDO document."""
        # This will accumulate a set of tags we've parsed that we don't
        # know how to deal with, since they do not have an associated class
        # defined.
        self.trace("FILE", tokens)
        try:
            tokens = self.SEGMENT(tokens.copy(), builder)
        except WrongToken:
            tokens = self.SEQUENCE(tokens, builder)
        return tokens
    top = FILE

    def SEGMENT(self, tokens, builder):
        self.trace("SEGMENT", tokens)
        tokens.match(tokens.SegmentStart)
        # builder.set_as_collection(core.Segment(tokens.current_position.get_last()))
        builder.begin_Segment(tokens.current_position.get_last())
        try:
            tokens = self.SEQUENCE(tokens.copy(), builder)
        except WrongToken:
            pass
        while 1:
            try:
                tokens.match(tokens.Comma)
            except WrongToken:
                break
            tokens = self.SEQUENCE(tokens, builder)
        tokens.match(tokens.SegmentEnd)
        # builder.reset_collection()
        builder.end_Segment()
        return tokens

    def SEQUENCE(self, tokens, builder):
        self.trace("SEQUENCE", tokens)
        tokens.match(tokens.SequenceStart)
        # builder.set_as_collection(core.Sequence(pos=tokens.current_position.get_last()))
        builder.begin_Sequence()
        self.last_note = self.default_note
        tokens = self.VOICE(tokens, builder)
        tokens.match(tokens.SequenceEnd)
        # builder.reset_collection()
        builder.end_Sequence()
        return tokens

    def VOICE(self, tokens, builder):
        self.trace("VOICE", tokens)
        while 1:
            try:
                tokens = self.BARLINE(tokens.copy(), builder)
            except WrongToken:
                try:
                    tokens = self.EVENT(tokens.copy(), builder)
                except WrongToken:
                    try:
                        tokens = self.CHORD(tokens.copy(), builder)
                    except WrongToken:
                        try:
                            tokens = self.TAG(tokens.copy(), builder, self.VOICE)
                        except WrongToken:
                            break
        return tokens

    def EVENT(self, tokens, builder):
        """Parses a note, rest or empty."""
        self.trace("EVENT", tokens)
        note = tokens.match(tokens.Note)

        # All of this madness below is to handle the passing of note
        # attributes from one to the next when note attributes are left
        # unspecified.  This is well defined in the Basic GUIDO specs.
        if note['num'] is None:
            if note['den'] is None:
                note['num'] = self.last_note['num']
                note['den'] = self.last_note['den']
                if note['dotting'] is None:
                    note['dotting'] = self.last_note['dotting']
            else:
                note['num'] = 1
        else:
            if note['den'] is None:
                note['den'] = self.last_note['den']
        if note['octave1'] is None:
            if note['octave2'] is None:
                note['octave1'] = self.last_note['octave1']
            else:
                note['octave1'] = note['octave2']
        self.last_note = note

        # Create the note or rest object
##         note_obj = core.EventFactory(
##             note['pitch_name'],
##             int(note['octave1']),
##             note['accidental'],
##             int(note['num']),
##             int(note['den']),
##             len(note['dotting']),
##             pos=tokens.current_position.get_last())

##         builder.add(note_obj)

        builder.add_Event(note['pitch_name'],
             int(note['octave1']),
             note['accidental'],
             int(note['num']),
             int(note['den']),
             len(note['dotting']),
             pos=tokens.current_position.get_last())
        return tokens

    def TAG(self, tokens, builder, inner):
        """Parse a tag."""
        self.trace("TAG", tokens)
        tag = tokens.match(tokens.Tag)
##         tag_obj = self._tag_factory(
##             tag['name'], tag['id'], tag['args'],
##             pos=tokens.current_position.get_last())
        tag_obj = builder.add_Tag(
            tag['name'], tag['id'], tag['args'],
            pos=tokens.current_position.get_last())

        name = tag_obj.name
        id = tag_obj.id

        # This is just for warnings
        if isinstance(tag_obj, core.DEFAULT_TAG):
            self.unknown_tags[tag['name']] = None

        if tag_obj.mode == "Begin":
            pass
        elif tag_obj.mode == "End":
            try:
                tokens = self.TAG_GROUPING(tokens.copy(), builder, tag_obj, inner)
            except WrongToken:
                pass
        else:
            try:
                tokens = self.TAG_GROUPING(tokens.copy(), builder, tag_obj, inner)
            except WrongToken:
                pass
        return tokens

    def TAG_GROUPING(self, tokens, builder, tag_obj, middle):
        self.trace("TAG_GROUPING", tokens)
        tokens.match(tokens.GroupingStart)
        tag_obj.mode = "Begin"
        tag_obj.use_parens = True
        builder.add_active_tag(tag_obj)
        tokens = middle(tokens.copy(), builder)
        tokens.match(tokens.GroupingEnd)
        # Can't pop, because we might have Begin and End tags overlapping this one
        builder.remove_active_tag(tag_obj)
        tag = copy(tag_obj)
        tag.mode = "End"
        tag.events = []
        builder.add(tag)
        return tokens

    def CHORD(self, tokens, builder):
        self.trace("CHORD", tokens)
        tokens.match(tokens.ChordStart)
##         builder.set_as_collection(core.Chord(
##             pos=tokens.current_position.get_last()))
        builder.begin_Chord(pos=tokens.current_position.get_last())
        tokens = self.CHORD_VOICE(tokens.copy(), builder)
        while 1:
            try:
                tokens.match(tokens.Comma)
            except WrongToken:
                break
            tokens = self.CHORD_VOICE(tokens, builder)
        tokens.match(tokens.ChordEnd)
##         builder.reset_collection()
        builder.end_Chord()
        return tokens

    def CHORD_VOICE(self, tokens, builder):
        self.trace("CHORD_VOICE", tokens)
        try:
            tokens = self.EVENT(tokens.copy(), builder)
        except WrongToken:
            while 1:
                try:
                    tokens = self.TAG(tokens.copy(), builder, self.CHORD_VOICE)
                except WrongToken:
                    break
        return tokens

    def BARLINE(self, tokens, builder):
        self.trace("BARLINE", tokens)
        if not tokens.match(tokens.Barline):
            return 1
##         barline = core.Barline(
##             pos=tokens.current_position.get_last())
##         builder.add(barline)
        builder.add_Barline(pos=tokens.current_position.get_last())
        return tokens
        
