"""
Miscellaneous data structures
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

from bisect import bisect_left, insort_left

class SortedListSet(object):
    def __init__(self, iterable=[]):
        data = list(iterable)
        data.sort()
        result = data[:1]
        for elem in data[1:]:
            if elem == result[-1]:
                continue
            result.append(elem)
        self.data = result
        
    def __repr__(self):
        return 'Set(' + repr(self.data) + ')'

    def __iter__(self):
        return iter(self.data)

    def __contains__(self, elem):
        data = self.data
        i = bisect_left(self.data, elem, 0)
        return i<len(data) and data[i] == elem

    def add(self, elem):
        insort_left(self.data, elem)

    def remove(self, elem):
        data = self.data
        i = bisect_left(self.data, elem, 0)
        if i<len(data) and data[i] == elem:
            del data[i]
 
    def _getotherdata(other):
        if not isinstance(other, Set):
            other = Set(other)
        return other.data
    _getotherdata = staticmethod(_getotherdata)

    def __cmp__(self, other, cmp=cmp):
        return cmp(self.data, Set._getotherdata(other))

    def union(self, other, find=bisect_left):
        i = j = 0
        x = self.data
        y = Set._getotherdata(other)
        result = Set([])        
        append = result.data.append
        extend = result.data.extend
        try:
            while 1:
                if x[i] == y[j]:
                    append(x[i])
                    i += 1
                    j += 1
                elif x[i] > y[j]:
                    cut = find(y, x[i], j)
                    extend(y[j:cut])
                    j = cut
                else:
                    cut = find(x, y[j], i)
                    extend(x[i:cut])
                    i = cut
        except IndexError:
            extend(x[i:])
            extend(y[j:])
        return result

    def intersection(self, other, find=bisect_left):
        i = j = 0
        x = self.data
        y = Set._getotherdata(other)
        result = Set([])        
        append = result.data.append
        try:
            while 1:
                if x[i] == y[j]:
                    append(x[i])
                    i += 1
                    j += 1
                elif x[i] > y[j]:
                    j = find(y, x[i], j)
                else:
                    i = find(x, y[j], i)
        except IndexError:
            pass
        return result
    
    def difference(self, other, find=bisect_left):
        i = j = 0
        x = self.data
        y = Set._getotherdata(other)
        result = Set([])        
        extend = result.data.extend
        try:
            while 1:
                if x[i] == y[j]:
                    i += 1
                    j += 1
                elif x[i] > y[j]:
                    j = find(y, x[i], j)
                else:
                    cut = find(x, y[j], i)
                    extend(x[i:cut])
                    i = cut
        except IndexError:
            extend(x[i:])
        return result

    def symmetric_difference(self, other, find=bisect_left):
        i = j = 0
        x = self.data
        y = Set._getotherdata(other)
        result = Set([])
        extend = result.data.extend
        try:
            while 1:
                if x[i] == y[j]:
                    i += 1
                    j += 1
                elif x[i] > y[j]:
                    cut = find(y, x[i], j)
                    extend(y[j:cut])
                    j = cut
                else:
                    cut = find(x, y[j], i)
                    extend(x[i:cut])
                    i = cut
        except IndexError:
            extend(x[i:])
            extend(y[j:])
        return result

class Grouper:
  def __init__(self):
     self.data = []

  def join(self, a, b=None):
     if a is None:
        return
     if b is None:
        for l in self.data:
           if a in l:
              return
        self.data.append([a])
        return
     al = bl = []
     for l in self.data:
        if a in l:
           al = l
           self.data.remove(al)
           break
     if al == []:
        al = [a]
     if not b in al:
        for l in self.data:
           if b in l:
              bl = l
              self.data.remove(bl)
              break
        if bl == []:
           bl = [b]
     self.data.append(al + bl)

__all__ = """
SortedListSet Grouper
""".split()
