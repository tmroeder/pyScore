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
        self.current_collection = core.Score(tokens.current_position)
        tokens = self.top(tokens)
        if self._warnings:
            if not tokens.at_end():
                sys.stderr.write("WARNING: Extra text at end of file\n")
            if len(self.unknown_tags.keys()):
                sys.stderr.write("WARNING: Unknown tags:\n")
                sys.stderr.write(textwrap.fill(', '.join(['\\' + x for x in self.unknown_tags.keys()])))
                sys.stderr.write("\n")
        return self.current_collection

    def _add(self, obj):
        """Adds an object to the current part."""
        self.current_collection.append(obj)
        for tag in self.active_tags:
            tag.tag(obj)

    def _set_as_collection(self, collection, add=True):
        if add:
            self._add(collection)
        last_collection = self.current_collection
        self.current_collection = collection
        return last_collection

    def _reset_collection(self, collection):
        self.current_collection = collection

    def _add_active_tag(self, tag_obj):
        assert isinstance(tag_obj, core.TAG)
        self.active_tags.append(tag_obj)

    def _remove_active_tag(self, tag_obj, tokens):
        assert isinstance(tag_obj, core.TAG)
        for i in range(len(self.active_tags) - 1, -1, -1):
            if (self.active_tags[i].name == tag_obj.name and
                self.active_tags[i].id == tag_obj.id):
                assert self.active_tags[i].mode == "Begin"
                del self.active_tags[i]
                return
        tokens.raise_error_wrong_token(
            "'\\%sEnd' appears before '\\%sBegin'" %
            (tag_obj.name, tag_obj.name))

    def FILE(self, tokens):
        """The top-level parsing node.  Initializes state and begins parsing
        a GUIDO document."""
        # This will accumulate a set of tags we've parsed that we don't
        # know how to deal with, since they do not have an associated class
        # defined.
        self.trace("FILE", tokens)
        try:
            tokens = self.SEGMENT(tokens.copy())
        except WrongToken:
            tokens = self.SEQUENCE(tokens)
        return tokens
    top = FILE

    def SEGMENT(self, tokens):
        self.trace("SEGMENT", tokens)
        tokens.match(tokens.SegmentStart)
        last_collection = self._set_as_collection(core.Segment(
            tokens.current_position.get_last()))
        try:
            tokens = self.SEQUENCE(tokens.copy())
        except WrongToken:
            pass
        while 1:
            try:
                tokens.match(tokens.Comma)
            except WrongToken:
                break
            tokens = self.SEQUENCE(tokens)
        tokens.match(tokens.SegmentEnd)
        self._reset_collection(last_collection)
        return tokens

    def SEQUENCE(self, tokens):
        self.trace("SEQUENCE", tokens)
        tokens.match(tokens.SequenceStart)
        last_collection = self._set_as_collection(core.Sequence(
            pos=tokens.current_position.get_last()))
        self.last_note = self.default_note
        tokens = self.VOICE(tokens)
        tokens.match(tokens.SequenceEnd)
        self._reset_collection(last_collection)
        return tokens

    def VOICE(self, tokens):
        self.trace("VOICE", tokens)
        while 1:
            try:
                tokens = self.BARLINE(tokens.copy())
            except WrongToken:
                try:
                    tokens = self.EVENT(tokens.copy())
                except WrongToken:
                    try:
                        tokens = self.CHORD(tokens.copy())
                    except WrongToken:
                        try:
                            tokens = self.TAG(tokens.copy(), self.VOICE)
                        except WrongToken:
                            break
        return tokens

    def EVENT(self, tokens):
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
        note_obj = core.EventFactory(
            note['pitch_name'],
            int(note['octave1']),
            note['accidental'],
            int(note['num']),
            int(note['den']),
            len(note['dotting']),
            pos=tokens.current_position.get_last())

        self._add(note_obj)
        return tokens

    def TAG(self, tokens, inner):
        """Parse a tag."""
        self.trace("TAG", tokens)
        tag = tokens.match(tokens.Tag)
        tag_obj = self._tag_factory(
            tag['name'], tag['id'], tag['args'],
            pos=tokens.current_position.get_last())

        name = tag_obj.name
        id = tag_obj.id

        # This is just for warnings
        if isinstance(tag_obj, core.DEFAULT_TAG):
            self.unknown_tags[tag['name']] = None

        if tag_obj.mode == "Begin":
            self._add(tag_obj)
            self._add_active_tag(tag_obj)
        elif tag_obj.mode == "End":
            self._remove_active_tag(tag_obj, tokens)
            self._add(tag_obj)
            try:
                tokens = self.TAG_GROUPING(tokens.copy(), tag_obj, inner)
            except WrongToken:
                pass
        else:
            self._add(tag_obj)
            try:
                tokens = self.TAG_GROUPING(tokens.copy(), tag_obj, inner)
            except WrongToken:
                pass
        return tokens

    def TAG_GROUPING(self, tokens, tag_obj, middle):
        self.trace("TAG_GROUPING", tokens)
        tokens.match(tokens.GroupingStart)
        tag_obj.mode = "Begin"
        tag_obj.use_parens = True
        self._add_active_tag(tag_obj)
        tokens = middle(tokens.copy())
        tokens.match(tokens.GroupingEnd)
        # Can't pop, because we might have Begin and End tags overlapping this one
        self._remove_active_tag(tag_obj, tokens)
        tag = copy(tag_obj)
        tag.mode = "End"
        tag.events = []
        self._add(tag)
        return tokens

    def CHORD(self, tokens):
        self.trace("CHORD", tokens)
        tokens.match(tokens.ChordStart)
        last_collection = self._set_as_collection(core.Chord(
            pos=tokens.current_position.get_last()))
        tokens = self.CHORD_VOICE(tokens.copy())
        while 1:
            try:
                tokens.match(tokens.Comma)
            except WrongToken:
                break
            tokens = self.CHORD_VOICE(tokens)
        tokens.match(tokens.ChordEnd)
        self._reset_collection(last_collection)
        return tokens

    def CHORD_VOICE(self, tokens):
        self.trace("CHORD_VOICE", tokens)
        try:
            tokens = self.EVENT(tokens.copy())
        except WrongToken:
            while 1:
                try:
                    tokens = self.TAG(tokens.copy(), self.CHORD_VOICE)
                except WrongToken:
                    break
        return tokens

    def BARLINE(self, tokens):
        self.trace("BARLINE", tokens)
        if not tokens.match(tokens.Barline):
            return 1
        barline = core.Barline(
            pos=tokens.current_position.get_last())
        self._add(barline)
        return tokens
        
