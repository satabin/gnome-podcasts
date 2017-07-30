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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from gi.repository import Gio, GLib, GObject, Tracker, TrackerMiner

from gnomepodcasts import log, safe

import threading
import schedule
import time
import datetime

import feedparser

import logging
logger = logging.getLogger(__name__)

@log
def parse_sparql(sparql_ret):
    ret = {}
    n_columns = sparql_ret.get_n_columns()
    for column in range(n_columns):
        t = sparql_ret.get_value_type(column)
        name = sparql_ret.get_variable_name(column)
        if any([t == Tracker.SparqlValueType.URI,
                t == Tracker.SparqlValueType.STRING]):
            value = sparql_ret.get_string(column)[0]
        elif t == Tracker.SparqlValueType.DATETIME:
            # Tracker returns ISO 8601 format
            value = time.strptime(sparql_ret.get_string(column)[0],
                                  "%Y-%m-%dT%H:%M:%S.%fZ")
        elif t == Tracker.SparqlValueType.BOOLEAN:
            value = sparql_ret.get_boolean(column)
        elif t == Tracker.SparqlValueType.INTEGER:
            value = sparql_ret.get_integer(column)
        elif t == Tracker.SparqlValueType.DOUBLE:
            value = sparql_ret.get_double(column)
        else:
            try:
                value = sparql_ret.get_string(column)[0]
            except Exception:
                value = None
                logger.error("Can't get string value from sparql. name: %s, type: %s", name, t)
        ret[name] = value
    return ret

class PodcastTracker(GObject.GObject):

    __gsignals__ = {
        'items-updated': (GObject.SignalFlags.RUN_LAST, None, ()),
        'feeds-updated': (GObject.SignalFlags.RUN_LAST, None, ()),
    }

    @log
    def __init__(self):
        GObject.GObject.__init__(self)
        bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        # subscribe to graph updates for FeedMessage
        bus.signal_subscribe(
            "org.freedesktop.Tracker1",
            "org.freedesktop.Tracker1.Resources",
            "GraphUpdated",
            "/org/freedesktop/Tracker1/Resources",
            "http://www.tracker-project.org/temp/mfo#FeedMessage",
            Gio.DBusSignalFlags.NONE,
            self.on_graph_updated)
        self.sparql = Tracker.SparqlConnection.get(None)

    @log
    def add_podcast(self, url, update_interval=30, cancellable=None, callback=None, user_data=None):
        """Add channel to fetching by tracker

        Args:
            url (str): URL of the channel.
            update_interval (Optional[int]): Update interval in minutes.
                                             Don't use less than 1 minute.
            cancellable (Optional[Gio.Cancellable]): Optional Gio.Cancellable
            callback (Optional[callable]): Optional callback for when the operation
                                           is finished
            user_data (Optional[object]): Data to the callback
        """

        query = """
        INSERT OR REPLACE {
          _:FeedSettings a mfo:FeedSettings ;
                           mfo:updateInterval %i .
          _:Feed a nie:DataObject, mfo:FeedChannel ;
                   mfo:feedSettings _:FeedSettings ;
                   nie:url "%s" ;
                   nie:keyword "podcast" }
        """ % (update_interval, url)

        self.sparql.update_async(query, GLib.PRIORITY_DEFAULT, cancellable,
                                 self._podcast_added_cb, (callback, user_data, update_interval, url))

    @log
    def _podcast_added_cb(self, connection, result, data):

        (callback, user_data, update_interval, url) = data

        try:
            result = connection.update_finish(result)
        except GLib.Error:
            result = False

        if callback:
            callback(user_data)

    @log
    def get_podcasts(self, url=None):
        """Returns list of podcasts

        Args:
            url (Optional[str]): URL of the podcast

        Returns:
            list of all podcasts limited to one podcast if url is
            not None
        """
        query = """
        SELECT
          nie:url(?chan) AS url
          nie:title(?chan) AS title
          mfo:image(?chan) AS image
          nie:description(?chan) AS description
          { ?chan a mfo:FeedChannel"""

        if url is not None:
            query += """; nie:url "%s" """ % url

        query += """
          }
        ORDER BY nie:title(?chan)
        """

        results = self.sparql.query(query)
        ret = []
        while (results.next(None)):
            ret.append(parse_sparql(results))

        return ret

    @log
    def on_graph_updated(self, connection, sender_name, object_path,
                         interface_name, signal_name, parameters, user_data=None):
        unpacked = parameters.unpack()
        # FIXME: handle deletes -- unpacked[1]
        GLib.idle_add(self._handle_insert_event, unpacked[2])

    @log
    def _handle_insert_event(self, items):
        self.emit('items-updated')
        self.emit('feeds-updated')
