"""
Lexer
A generic tokenizing lexer
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
import re
try:
    import textwrap
except ImportError:
    from pyScore.util.backport import textwrap

########################################
# EXCEPTIONS

class ParseError:
    def __init__(self, position, message):
        self.s = position.s
        self.line = position.line
        self.position = position.pos
        self.message = message

    def __repr__(self):
        s = self.s
        i = 0
        for i in range(max(self.position, 0),
                       max(self.position - 35, 0), -1):
            if s[i] in "\n":
                break
        start = i
        for i in range(min(self.position + 1, len(s)),
                       min(self.position + 35, len(s))):
            if s[i] in "\n":
                break
        end = i + 1
        result = "\nAt line %d:\n" % self.line
        result += s[start:end].replace("\n", "")
        result += "\n" + " " * (self.position - start) + "^\n"
        result += textwrap.fill(self.message)
        return result

    __str__ = __repr__

class WrongToken(ParseError):
    def __init__(self, position, found):
        result = "Parse error.  Cannot have %s here." % found
        ParseError.__init__(self, position, result)


########################################
# TOKENS

class Token:
    def __init__(self, match_group=None):
        self.match_group = match_group
        if match_group != None:
            self.dict = match_group.groupdict()
        else:
            self.dict = {}

    def __repr__(self):
        if self.match_group != None:
            groups = repr(self.dict)
        else:
            groups = "None"
        return "<%s: %s>" % (self.__class__.__name__, groups)

    def __getitem__(self, key):
        return self.dict[key]

    def __setitem__(self, key, val):
        self.dict[key] = val
    
    def match(cls, str, pos):
        m = cls.regex.match(str, pos)
        if m:
            return cls(m)
        return None
    match = classmethod(match)

class StartOfFileToken(Token):
    pass

class EndOfFileToken(Token):
    pass

class WhitespaceToken(Token):
    regex = re.compile("\s")

########################################
# TOKENIZER

class Position:
    def __init__(self, s, pos=0, line=1):
        self.s = s + "  \n"
        self.pos = pos
        self.last_pos = pos
        self.line = line
        self.last_line = line

    def update_max(self, pos):
        self.pos = max(self.pos, pos.pos)
        self.line = max(self.line, pos.line)

    def get_last(self):
        return Position(self.s, self.last_pos, self.last_line)

class Tokenizer:
    filtered_tokens = (WhitespaceToken,)
    def __init__(self, s, pos = 0, line = 1, deepest = None):
        self.current_position = Position(s, pos, line)
        if deepest == None:
            self.deepest_position = Position(s, pos, line)
        else:
            self.deepest_position = deepest
            deepest.update_max(self.current_position)

    def copy(self):
        position = self.current_position
        return self.__class__(position.s, position.pos, position.line, self.deepest_position)

    def match(self, token):
        position = self.current_position
        position.last_pos = position.pos
        position.last_line = position.line
        if position.pos > len(position.s):
            return None
        found_whitespace = True
        filtered_tokens = self.filtered_tokens
        while found_whitespace:
            found_whitespace = False
            for tok in filtered_tokens:
                match = tok.match(position.s, position.pos)
                if match != None:
                    end = match.match_group.end()
                    position.line += position.s.count('\n', position.pos, end)
                    position.pos = end
                    found_whitespace = True
                    break
        match = token.match(position.s, position.pos)
        if match != None:
            end = match.match_group.end()
            position.line += position.s.count('\n', position.pos, end)
            position.pos = end
            self.deepest_position.update_max(position)
            return match
        self.deepest_position.update_max(position)
        self.raise_error_wrong_token(token)

    def raise_error(self, message):
        raise ParseError(self.s, self.pos, self.line, message)

    def raise_error_wrong_token(self, expected):
        position = self.deepest_position
        found = None
        for tok in self.tokens:
            if tok.match(position.s, position.pos):
                found = tok.__name__
                break
        if found == None:
            found = "<unknown>"
        raise WrongToken(self.deepest_position, found)

    def at_end(self):
        position = self.current_position
        return not len(position.s[position.pos:].strip())
