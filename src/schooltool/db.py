#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2003 Shuttleworth Foundation
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
"""
The persistent helper objects for SchoolTool.

$Id$
"""
import UserDict
from persistence import Persistent
from persistence.list import PersistentList
from persistence.dict import PersistentDict

__metaclass__ = type


class PersistentKeysDict(Persistent, UserDict.DictMixin):
    """A PersistentDict which uses persistent objects as keys by
    relying on their _p_oids.

    If an object used as a key does not yet have a _p_oid, it is added
    to self._p_jar and assigned a _p_oid.  Thus, PersistentKeysDict()
    has to be added to the ZODB connection before being used.
    """

    def _getvdata(self):
        if not hasattr(self, '_v_data'):
            self._v_data = {}
        return self._v_data
    _tmpdata = property(_getvdata)

    def __init__(self):
        self._data = PersistentDict()

    def __setitem__(self, key, value):
        """Adds a value to the dict.

        If a key object does not yet have _p_oid, it is added to the
        current connection (self._p_jar).
        """
        self.checkKey(key)
        if key._p_oid is None or self._p_jar is None:
            self._tmpdata[id(key)] = (key, value)
        else:
            self._data[key._p_oid] = value

    def __getitem__(self, key):
        self.checkKey(key)
        try:
            if id(key) in self._tmpdata:
                return self._tmpdata[id(key)][1]
            else:
                return self._data[key._p_oid]
        except KeyError:
            raise KeyError, key

    def __delitem__(self, key):
        self.checkKey(key)
        try:
            if id(key) in self._tmpdata:
                del self._tmpdata[id(key)]
            else:
                del self._data[key._p_oid]
        except KeyError:
            raise KeyError, key

    def keys(self):
        # XXX returning a lazy sequence is one optimization we might make
        jar = self._p_jar
        return ([jar.get(key) for key in self._data] + 
                [key for key, value in self._tmpdata.itervalues()])

    def __contains__(self, key):
        self.checkKey(key)
        return id(key) in self._tmpdata or key._p_oid in self._data

    def __iter__(self):
        jar = self._p_jar
        for key in self._data:
            yield jar.get(key)
        for key, value in self._tmpdata.itervalues():
            yield key

    def __len__(self):
        return len(self._data) + len(self._tmpdata)

    def checkKey(self, key):
        if not hasattr(key, '_p_oid'):
            raise TypeError("The key must be persistent (got %r)" % (key, ))

    def __getstate__(self):
        data = self._data
        jar = self._p_jar
        assert jar is not None
        for key, value in self._tmpdata.itervalues():
            if key._p_oid is None:
                jar.add(key)
            data[key._p_oid] = value
        self._tmpdata.clear()
        return Persistent.__getstate__(self)


class PersistentKeysSet(Persistent):
    """A set for persistent objects that uses PersistentKeysDict as a
    backend.
    """

    def __init__(self):
        self._data = PersistentKeysDict()

    def add(self, item):
        if item not in self._data:
            self._data[item] = None

    def __iter__(self):
        return iter(self._data)

    def remove(self, item):
        del self._data[item]

    def __len__(self):
        return len(self._data)


class PersistentPairKeysDict(Persistent, UserDict.DictMixin):
    """A dict indexed strictly by pairs (persistent, hashable)."""

    def __init__(self):
        self._data = PersistentKeysDict()

    def __setitem__(self, (persistent, hashable), value):
        if persistent not in self._data:
            self._data[persistent] = {}
        d = self._data[persistent]
        d[hashable] = value
        self._data[persistent] = d

    def __getitem__(self, (persistent, hashable)):
        return self._data[persistent][hashable]

    def __delitem__(self, (persistent, hashable)):
        d = self._data[persistent]
        del d[hashable]
        if d:
            self._data[persistent] = d
        else:
            del self._data[persistent]

    def keys(self):
        L = []
        data = self._data
        for persistent in data:
            L += [(persistent, hashable)
                  for hashable in data[persistent]]
        return L

    def __contains__(self, (persistent, hashable)):
        return (persistent in self._data and
                hashable in self._data[persistent])

    def __len__(self):
        count = 0
        data = self._data
        for persistent in data:
            count += len(data[persistent])
        return count

    def __iter__(self):
        data = self._data
        for persistent in data:
            for hashable in data[persistent]:
                yield persistent, hashable

    def iteritems(self):
        data = self._data
        for persistent in data:
            for hashable, value in data[persistent].iteritems():
                yield (persistent, hashable), value
