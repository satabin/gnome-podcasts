# Copyright (c) 2013 Vadim Rutkovsky <vrutkovs@redhat.com>
# Copyright (c) 2013 Guillaume Quintard <guillaume.quintard@gmail.com>
# Copyright (c) 2013 Eslam Mostafa <cseslam@gmail.com>
# Copyright (c) 2013 Manish Sinha <manishsinha@ubuntu.com>
# Copyright (C) 2017 Lucas Satabin <lucas.satabin@gnieh.org>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.from itertools import chain

from time import time
import logging

logger = logging.getLogger(__name__)
tabbing = 0


def log(fn):
    """Decorator to log function details.

    Shows function signature, return value, time elapsed, etc.
    Logging will be done if the debug flag is set.
    :param fn: the function to be decorated
    :return: function wrapped for logging
    """
    if logger.getEffectiveLevel() > logging.DEBUG:
        return fn

    def wrapped(*v, **k):
        global tabbing
        name = fn.__qualname__
        filename = fn.__code__.co_filename.split('/')[-1]
        lineno = fn.__code__.co_firstlineno

        params = ", ".join(map(repr, chain(v, k.values())))

        if 'rateLimitedFunction' not in name:
            logger.debug("%s%s(%s)[%s:%s]", '|' * tabbing, name, params,
                         filename, lineno)
        tabbing += 1
        start = time()
        retval = fn(*v, **k)
        elapsed = time() - start
        tabbing -= 1
        elapsed_time = ''
        if elapsed > 0.1:
            elapsed_time = ', took %02f' % elapsed
        if (elapsed_time
                or retval is not None):
            if 'rateLimitedFunction' not in name:
                logger.debug("%s  returned %s%s", '|' * tabbing, repr(retval),
                             elapsed_time)
        return retval

    return wrapped

def safe(value):
    class SafeAttribute(object):

        def __init__(self, wrapped):
            self._obj = wrapped

        def __getattribute__(self, name):
            return getattr(object.__getattribute__(self, "_obj"), name)

        def __getattr__(self, name):
            return None

    return SafeAttribute(value)
