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
            tv = GLib.TimeVal.from_iso8601(sparql_ret.get_string(column)[0])
            value = GLib.DateTime.new_from_timeval_local(tv[1])
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

class PodcastMiner(TrackerMiner.Miner):

    __gtype_name__ = 'PodcastMiner'

    def __init__ (self):
        TrackerMiner.Miner.__init__ (self,
                                     name="PodcastMiner",
                                     progress=0,
                                     status="fine")
        self.connect ("started", self.started_cb)
        self.connect ("stopped", self.stopped_cb)

        bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        # subscribe to graph updates for FeedChannel
        bus.signal_subscribe(
            "org.freedesktop.Tracker1",
            "org.freedesktop.Tracker1.Resources",
            "GraphUpdated",
            "/org/freedesktop/Tracker1/Resources",
            "http://www.tracker-project.org/temp/mfo#FeedChannel",
            Gio.DBusSignalFlags.NONE,
            self.on_graph_updated)
        self.sparql = Tracker.SparqlConnection.get(None)

        self._update_task = self.run_continuously()

        # the dictionary of scheduled feed updates
        self._scheduled = {}

        # retrieve all existing podcasts and schedule them
        query = """
        SELECT
            nie:url(?chan) AS url
            mfo:updateInterval(mfo:feedSettings(?chan)) as interval
            tracker:id(?chan) as id
        { ?chan a mfo:FeedChannel;
          nie:keyword "podcast" . }"""
        results = self.sparql.query(query)
        while (results.next(None)):
            parsed = parse_sparql(results)
            self.schedule_podcast(parsed['interval'], parsed['url'], parsed['id'])

        # Say to initable that we are ok
        self.init(None)

    def schedule_podcast(self, interval, url, ident):
        logger.warning("Scheduling new job for %s every %s minutes" % (url, interval))
        # schedule the job
        job = schedule.every(interval).minutes.do(self.update_feed, url)
        # and save the scheduled job and the interval
        self._scheduled[ident] = (interval, job)
        # run it now!
        job.run()

    @log
    def update_feed(self, url):

        logger.warning("updating feed %s" % url)

        query = """
        SELECT
            ?chan AS urn
            nie:version(?chan) AS etag
            nie:contentLastModified(?chan) as modified
            mfo:updateInterval(mfo:feedSettings(?chan)) as interval
        { ?chan a mfo:FeedChannel;
          nie:url "%s". }""" % url
        results = self.sparql.query(query)
        podcast = None
        while not podcast and results.next(None):
            podcast = parse_sparql(results)

        urn = podcast['urn']

        pod = safe(feedparser.parse(url, etag=podcast['etag'], modified=podcast['modified']))

        if pod.status != 304:

            feed = safe(pod.feed)

            title = feed.title
            if not title:
                # no title, returning
                return

            update = """INSERT OR REPLACE {
              <%s> nie:title "%s" """ % (urn, title)

            # it was actually modified, update the graph
            etag = pod.etag
            if etag:
                update += """;
                nie:version "%s" """ % etag

            modified = pod.modified_parsed
            if modified:
                modified = datetime.datetime(*modified[:6]).isoformat()
                update += """;
                nie:contentLastModified "%s" """ % modified

            description = feed.description
            if description:
                update += """;
                nie:description "%s" """ % description

            copyright = feed.copyright
            if copyright:
                update += """;
                nie:copyright "%s" """ % copyright


            image = feed.image.url
            if image:
                update += """;
                mfo:image "%s" """ % image

            publisher = feed.publisher
            if publisher:
                update += """;
                nco:publisher "%s" """ % publisher

            categories = feed.categories
            if categories:
                for (_, cat) in categories:
                    update += """;
                    nie:keyword "%s" """ % cat


            entries = pod.entries

            for entry in entries:
                entry = safe(entry)
                #print("> %s" % entry.title)
                #print(">> %s" % entry.author)
                #print(">> %s" % entry.link)
                #print(">> %s" % entry.description)
                #print(">> %s" % time.mktime(entry.published_parsed))
                #print(">> %s" % time.mktime(entry.updated_parsed))
                #print(">> %s" % entry.enclosures)
                #print(">> %s" % entry.itunes_duration)

            update += "}"

            self.sparql.update_async(update, GLib.PRIORITY_DEFAULT, None,
                                     self._podcast_updated_cb, (None, None))

    @log
    def _podcast_updated_cb(self, connection, result, data):
        result = connection.update_finish(result)

    def run_continuously(self, interval=1):
        cease_continuous_run = threading.Event()

        class ScheduleThread(threading.Thread):
            @classmethod
            def run(cls):
                while not cease_continuous_run.is_set():
                    schedule.run_pending()
                    time.sleep(interval)

        self._continuous_thread = ScheduleThread()

        return cease_continuous_run

    @log
    def on_graph_updated(self, connection, sender_name, object_path,
                         interface_name, signal_name, parameters, user_data=None):
        unpacked = parameters.unpack()
        updated = {i for (_, i, _, _) in unpacked[2]}
        deleted = {i for (_, i, _, _) in unpacked[1] if not i in updated}
        if deleted:
            self.handle_deletes(deleted)
        if updated:
            self.handle_updates(updated)

    def handle_deletes(self, deleted):
        if deleted:
            for i in deleted:
                (_, job) = self._scheduled[i]
                schedule.cancel_job(job)

            delete = """
            DELETE { ?msg nmo:communicationChannel ?chan }
                WHERE  { ?msg a mfo:FeedMessage;
	            nmo:communicationChannel ?chan .
	            FILTER (tracker:id(?chan) IN (%s))
	        }
	        """ % ",".join(set(str(i) for i in deleted))

            self.sparql.update_async(delete, GLib.PRIORITY_DEFAULT, None,
                                     self._message_unbound_cb, (None, None))


    def handle_updates(self, updated):
        # query the settings and url for updated identifiers
        query = """
        SELECT ?url ?interval tracker:id(?urn) as id
	                       WHERE {
	                         ?urn a mfo:FeedChannel ;
	                                mfo:feedSettings ?settings ;
	                                nie:url ?url .
	                         ?settings mfo:updateInterval ?interval
        """

        if updated:
            query += """. FILTER (tracker:id(?urn) IN (%s))
            """ % ",".join(set(str(i) for i in updated))

        query += "}"

        results = self.sparql.query(query)
        while (results.next(None)):
            parsed = parse_sparql(results)
            url = parsed['url']
            interval = parsed['interval']
            ident = parsed['id']
            if ident in self._scheduled:
                (old_int, job) = self._scheduled[ident]
                if old_int != interval:
                    schedule.cancel_job(job)
                    del self._scheduled[ident]
                    self.schedule_podcast(interval, url, ident)
            else:
                self.schedule_podcast(interval, url, ident)

    @log
    def _message_unbound_cb(self, connection, result, data):
        result = connection.update_finish(result)

        delete = """
        DELETE { ?msg a rdfs:Resource }
            WHERE  { ?msg a mfo:FeedMessage .
            FILTER(!BOUND(nmo:communicationChannel(?msg)))
        }"""

        self.sparql.update_async(delete, GLib.PRIORITY_DEFAULT, None,
                                 None, (None, None))


    def started_cb (self, x):
        self._continuous_thread.start()
        logger.debug("Podcast miner started")

    def stopped_cb (self, x):
        self._update_task.set()
        logger.debug("Podcast miner stopped")

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
