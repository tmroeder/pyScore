"""
Definition of 'Basic GUIDO' tempo tags
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

from pyScore.Guido.objects.core import TAG
import re

class TEMPO:
    tempi = {
        'largo': '1/4=54',
        'lento': '1/4=58',
        'adagio': '1/4=63',
        'moderato': '1/4=70',
        'andante': '1/4=72',
        'allegro': '1/4=114',
        'vivace': '1/4=120',
        'presto': '1/4=126' }

    _regex_tempo = re.compile(r"(?P<num>[0-9]+)/(?P<den>[0-9]+)(?P<dots>\.?\.?)\=(?P<bpm>[0-9]+)")
    
    def __init__(self, name, id, args_list, args_dict, *args, **kwargs):
        TAG.__init__(self, name, id, args_list, args_dict, *args, **kwargs)
        self.tempo_name = None
        if len(args_list) == 1:
            arg = args_list[0].lower()
            if self.tempi.has_key(arg):
                self.tempo_name = args_list[0]
                self.parse_tempo(self.tempi[arg])
            else:
                try:
                    self.parse_tempo(arg)
                except:
                    self.raise_error("I don't know how fast '%s' is.  Please specify a second argument of the form '1/4=120'." % (arg))
        elif len(args_list) == 2:
            self.tempo_name = args_list[0]
            self.parse_tempo(args_list[1])

    def parse_tempo(self, s):
        match = self._regex_tempo.match(s)
        if not match:
            self.raise_error(
                "'%s' is not a valid tempo specification.  Must be of the form '1/4=120'." % s)
        else:
            d = match.groupdict()
            self.num = int(d['num'])
            self.den = int(d['den'])
            self.dots = len(d['dots'])
            self.bpm = int(d['bpm'])

class tempo(TEMPO, TAG):
    def __init__(self, name, id, args_list, args_dict, *args, **kwargs):
        self.num = 1
        self.den = 4
        self.bpm = 120
        self.dots = 0
        if len(args_list) < 1:
            self.raise_error("\\tempo tag must have at least one argument")
        TEMPO.__init__(self, name, id, args_list, args_dict, *args, **kwargs)

class accelerando(TEMPO, TAG):
    pass
accel = accelerando

class ritardando(TEMPO, TAG):
    pass
rit = ritardando

__all__ = '''
tempo
accelerando accel
ritardando rit
'''.split()
