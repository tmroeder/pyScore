"""
Various dictionaries and lists to support conversion
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

from pyScore.util.rational import Rat

DIVISIONS = 144
acceptable_dynamic_names = 'p pp ppp pppp ppppp pppppp f ff fff ffff fffff ffffff mp mf sf sfp sfpp fp rf rfz sfz sffz fz'.split()
g2m_accidental = {
   '&&': 'double-flat',
   '&': 'flat',
   '#': 'sharp',
   '##': 'sharp'}
g2m_duration_type = [
   (Rat(1,256), '256th'),
   (Rat(1,128), '128th'),
   (Rat(1,64), '64th'),
   (Rat(1,32), '32nd'),
   (Rat(1,16), '16th'),
   (Rat(1,8), 'eighth'),
   (Rat(1,4), 'quarter'),
   (Rat(1,2), 'half'),
   (Rat(1,1), 'whole'),
   (Rat(2,1), 'breve')
   ]
g2m_clef_type = {
   'g': 'G',
   'f': 'F',
   'c': 'C',
   'perc': 'percussion'}
m2g_clef_type = {
   'G': 'g',
   'F': 'f',
   'C': 'c',
   'percussion': 'perc'}
m2g_clef_name = {
   'g2': 'treble',
   'f4': 'bass',
   'c4': 'tenor',
   'c3': 'treble'}
g2m_named_meter = {
   'C': 'common',
   'C/': 'cut'}
m2g_time_symbol = {
   'common': 'C',
   'cut': 'C/'}
g2m_octave_types = {
   -1: 'down',
   0: 'stop',
   1: 'up'}
g2m_articulations = ('accent', 'staccato', 'tenuto')
m2g_accidental = {-2: '&&',
                  -1: '&',
                  0: '',
                  1: '#',
                  2: '##'}
g2m_ornaments = {'trill': 'trill-mark',
                 'turn': 'turn',
                 'mordent': 'mordent'}
supported_creators = ('composer', 'lyricist')
m2g_key = {
   'major': { 0: 'C',
              1: 'G', 2: 'D', 3: 'A', 4: 'E', 5: 'B', 6: 'F#', 7: 'C#',
              -1: 'F', -2: 'B&', -3: 'E&', -4: 'A&', -5: 'D&', -6: 'G&', -7: 'C&' },
   'minor': { 0: 'a',
              1: 'e', 2: 'b', 3: 'f#', 4: 'c#', 5: 'g#', 6: 'd#', 7: 'a#',
              -1: 'd', -2: 'g', -3: 'c', -4: 'f', -5: 'b&', -6: 'e&', -7: 'a&' }
   }
m2g_octave_shift = {
   'up': '+',
   'down': '-'}
