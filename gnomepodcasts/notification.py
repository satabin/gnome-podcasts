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

from gi.repository import GLib, Notify

from gettext import gettext as _

from gnomepodcasts import log
import logging
logger = logging.getLogger(__name__)


class NotificationManager:

    def __repr__(self):
        return '<NotificationManager>'

    @log
    def __init__(self, player):
        self._player = player

        self._notification = Notify.Notification()

        self._notification.set_category('x-gnome.podcasts')
        self._notification.set_hint('action-icons', GLib.Variant('b', True))
        self._notification.set_hint('resident', GLib.Variant('b', True))
        self._notification.set_hint('desktop-entry', GLib.Variant('s', 'gnome-podcasts'))

    @log
    def _set_actions(self, playing):
        self._notification.clear_actions()

        if (Notify.VERSION_MINOR > 7) or (Notify.VERSION_MINOR == 7 and Notify.VERSION_MICRO > 5):
            self._notification.add_action('media-skip-backward', _("Previous"),
                                          self._go_previous, None)
            if playing:
                self._notification.add_action('media-playback-pause', _("Pause"),
                                              self._pause, None)
            else:
                self._notification.add_action('media-playback-start', _("Play"),
                                              self._play, None)
            self._notification.add_action('media-skip-forward', _("Next"),
                                          self._go_next, None)

    @log
    def _go_previous(self, notification, action, data):
        self._player.play_previous()

    @log
    def _go_next(self, notification, action, data):
        self._player.play_next()

    @log
    def _play(self, notification, action, data):
        self._player.play()

    @log
    def _pause(self, notification, action, data):
        self._player.pause()
