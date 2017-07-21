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

from gettext import gettext as _

from gi.repository import Gtk, Gio, GLib

from gnomepodcasts import log
from gnomepodcasts.toolbar import Toolbar

class Window(Gtk.ApplicationWindow):

    def __repr__(self):
        return '<Window>'

    @log
    def __init__(self, app):
        Gtk.ApplicationWindow.__init__(self,
                                       application=app,
                                       title=_("Podcasts"))
        self.connect('focus-in-event', self._windows_focus_cb)
        self.settings = Gio.Settings.new('org.gnome.Podcasts')
        self.set_size_request(200, 100)
        self.set_icon_name('gnome-podcasts')
        self.notification_handler = None
        self._loading_counter = 0

        self.prev_view = None
        self.curr_view = None

        self.miner = app.miner
        self.tracker = app.tracker

        size_setting = self.settings.get_value('window-size')
        if isinstance(size_setting[0], int) and isinstance(size_setting[1], int):
            self.resize(size_setting[0], size_setting[1])

        position_setting = self.settings.get_value('window-position')
        if len(position_setting) == 2 \
           and isinstance(position_setting[0], int) \
           and isinstance(position_setting[1], int):
            self.move(position_setting[0], position_setting[1])

        if self.settings.get_value('window-maximized'):
            self.maximize()

        self._setup_view()
        #self._setup_loading_notification()
        #self._setup_playlist_notification()

        self.window_size_update_timeout = None
        self.connect("window-state-event", self._on_window_state_event)
        self.connect("configure-event", self._on_configure_event)
        self.connect("destroy", self._on_destroy)

    @log
    def _setup_view(self):
        self._box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        #self.player = Player(self)
        #self.selection_toolbar = SelectionToolbar()
        self.toolbar = Toolbar(self)
        self.views = []
        self._stack = Gtk.Stack(
            transition_type=Gtk.StackTransitionType.CROSSFADE,
            transition_duration=100,
            visible=True,
            can_focus=False)

        # Add the 'background' styleclass so it properly hides the
        # bottom line of the searchbar
        self._stack.get_style_context().add_class('background')

        self._overlay = Gtk.Overlay(child=self._stack)
        #self._overlay.add_overlay(self.toolbar.dropdown)
        self.set_titlebar(self.toolbar.header_bar)
        #self._box.pack_start(self.toolbar.searchbar, False, False, 0)
        self._box.pack_start(self._overlay, True, True, 0)
        #self._box.pack_start(self.player.actionbar, False, False, 0)
        #self._box.pack_start(self.selection_toolbar.actionbar, False, False, 0)
        self.add(self._box)

        #def songs_available_cb(available):
        #    if available:
        #        self._switch_to_player_view()
        #    else:
        #        self._switch_to_empty_view()

        #Query()
        #if Query.music_folder:
        #    grilo.songs_available(songs_available_cb)
        #else:
        #    self._switch_to_empty_view()

        #self.toolbar._search_button.connect('toggled', self._on_search_toggled)
        #self.toolbar.connect('selection-mode-changed', self._on_selection_mode_changed)
        #self.selection_toolbar._add_to_playlist_button.connect(
        #    'clicked', self._on_add_to_playlist_button_clicked)
        #self.selection_toolbar._remove_from_playlist_button.connect(
        #    'clicked', self._on_remove_from_playlist_button_clicked)

        self.toolbar.header_bar.show()
        self._overlay.show()
        #self.player.actionbar.show_all()
        self._box.show()
        self.show()

    @log
    def store_window_size_and_position(self, widget):
        size = widget.get_size()
        self.settings.set_value('window-size', GLib.Variant('ai', [size[0], size[1]]))

        position = widget.get_position()
        self.settings.set_value('window-position', GLib.Variant('ai', [position[0], position[1]]))
        GLib.source_remove(self.window_size_update_timeout)
        self.window_size_update_timeout = None
        return False


    @log
    def _on_configure_event(self, widget, event):
        if self.window_size_update_timeout is None:
            self.window_size_update_timeout = GLib.timeout_add(500, self.store_window_size_and_position, widget)

    @log
    def _on_window_state_event(self, widget, event):
        self.settings.set_boolean('window-maximized', 'GDK_WINDOW_STATE_MAXIMIZED' in event.new_window_state.value_names)

    @log
    def _grab_media_player_keys(self):
        self.proxy = Gio.DBusProxy.new_sync(Gio.bus_get_sync(Gio.BusType.SESSION, None),
                                            Gio.DBusProxyFlags.NONE,
                                            None,
                                            'org.gnome.SettingsDaemon.MediaKeys',
                                            '/org/gnome/SettingsDaemon/MediaKeys',
                                            'org.gnome.SettingsDaemon.MediaKeys',
                                            None)
        self.proxy.call_sync('GrabMediaPlayerKeys',
                             GLib.Variant('(su)', ('Podcasts', 0)),
                             Gio.DBusCallFlags.NONE,
                             -1,
                             None)
        self.proxy.connect('g-signal', self._handle_media_keys)

    @log
    def _windows_focus_cb(self, window, event):
        try:
            self._grab_media_player_keys()
        except GLib.GError:
            # We cannot grab media keys if no settings daemon is running
            pass

    @log
    def _handle_media_keys(self, proxy, sender, signal, parameters):
        """
        if signal != 'MediaPlayerKeyPressed':
            print('Received an unexpected signal \'%s\' from media player'.format(signal))
            return
        response = parameters.get_child_value(1).get_string()
        if 'Play' in response:
            self.player.play_pause()
        elif 'Stop' in response:
            self.player.Stop()
        elif 'Next' in response:
            self.player.play_next()
        elif 'Previous' in response:
            self.player.play_previous()
        """
        pass

    @log
    def on_back_button_clicked(self, widget):
        self._stack.set_visible_child(self._stack.previous_view)
        self._stack.previous_view = None
        self._stack.remove(self.feed_view)
        self.toolbar.set_state(ToolbarState.MAIN)
        self.feed_view = None

    def _on_destroy(self, window):
        if self.miner:
            self.miner.stop()
