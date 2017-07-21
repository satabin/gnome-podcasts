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

from gi.repository import Gtk, GLib, GObject

from gnomepodcasts import log

class ToolbarState:
    MAIN = 0
    CHILD_VIEW = 1
    SEARCH_VIEW = 2

class Toolbar(GObject.GObject):

    __gsignals__ = {
        'state-changed': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'toggle-starred': (GObject.SignalFlags.RUN_FIRST, None, (bool,)),
    }

    @log
    def __init__(self, window):
        GObject.GObject.__init__(self)
        self.window = window
        self._stack_switcher = Gtk.StackSwitcher(
            margin_top=2, margin_bottom=2, can_focus=False, halign="center")

        self._ui = Gtk.Builder()
        self._ui.add_from_resource('/org/gnome/Podcasts/ui/headerbar.ui')
        self.header_bar = self._ui.get_object('header-bar')
        self.header_bar.set_custom_title(self._stack_switcher)

        self.add_toggle_button = self._ui.get_object('add-toggle-button')
        self.add_popover = self._ui.get_object('add-popover')
        self.add_popover.hide()
        self.add_toggle_button.set_popover(self.add_popover)

        self.button_stack = self._ui.get_object('add-button-stack')

        self.new_url = self._ui.get_object('new-url')
        self.new_url.connect('changed', self.on_new_url_changed)
        self.add_button = self._ui.get_object('add-button')
        self.add_button.connect('clicked', self._add_new_feed)

        self._back_button = self._ui.get_object('back-button')
        self._back_button.connect('clicked', self.window.on_back_button_clicked)

        self._search_button = self._ui.get_object('search-button')
        #self._search_button.bind_property('active',
        #                                  self.window.search_bar, 'search-mode-enabled',
        #                                  GObject.BindingFlags.BIDIRECTIONAL)

        self.set_state(ToolbarState.MAIN)

        self._stack_switcher.show()

    @log
    def reset_header_title(self):
        self.header_bar.set_custom_title(self._stack_switcher)

    @log
    def set_state(self, state, btn=None):
        self._state = state
        self._update()
        self.emit('state-changed')

    @log
    def _update(self):
        if self._state != ToolbarState.MAIN:
            self.header_bar.set_custom_title(None)
        else:
            self.reset_header_title()

        self._back_button.set_visible(self._state == ToolbarState.CHILD_VIEW)
        self._search_button.set_visible(self._state != ToolbarState.CHILD_VIEW)
        #self._starred_button.set_visible(self._state == ToolbarState.CHILD_VIEW)
        self.add_toggle_button.set_visible(self._state != ToolbarState.CHILD_VIEW)

    @log
    def _add_new_feed(self, button):
        new_url = self.new_url.get_text()
        self.window.tracker.add_podcast(new_url, 30, None, self._podcast_added)
        self.button_stack.set_visible_child_name('spinner')
        self.new_url.set_sensitive(False)

    @log
    def _podcast_added(self, user_data=None):
        self.button_stack.set_visible_child_name('button')
        self.new_url.set_sensitive(True)
        self.new_url.set_text('')
        self.add_popover.hide()

    def on_new_url_changed(self, entry):
        text = self.new_url.get_text()
        already_subscribed_label = self._ui.get_object("add-box-already-subscribed-label")
        if len(text) == 0:
            self.add_button.set_sensitive(False)
            already_subscribed_label.set_visible(False)
        else:
            if not GLib.uri_parse_scheme(text):
                self.add_button.set_sensitive(False)
                already_subscribed_label.set_visible(False)
                return
            if len(self.window.tracker.get_podcasts(text)) == 0:
                already_subscribed_label.set_visible(False)
                self.add_button.set_sensitive(True)
            else:
                self.add_button.set_sensitive(False)
                already_subscribed_label.set_visible(True)
