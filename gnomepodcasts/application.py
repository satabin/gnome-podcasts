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

from gi.repository import Gtk, Gio, GLib, Gdk, Notify

from gnomepodcasts import log
from gnomepodcasts.notification import NotificationManager
from gnomepodcasts.tracker import PodcastTracker
from gnomepodcasts.window import Window

class Application(Gtk.Application):
    def __repr__(self):
        return '<Application>'

    @log
    def __init__(self):
        Gtk.Application.__init__(self, application_id='org.gnome.Podcasts',
                                 flags=Gio.ApplicationFlags.FLAGS_NONE)
        GLib.set_application_name(_("Podcasts"))
        GLib.set_prgname('gnome-podcasts')
        self._settings = Gio.Settings.new('org.gnome.Podcasts')
        self._init_style()
        self._window = None
        self.tracker = None

    def _init_style(self):
        css_provider_file = Gio.File.new_for_uri(
            'resource:///org/gnome/Podcasts/application.css')
        css_provider = Gtk.CssProvider()
        css_provider.load_from_file(css_provider_file)
        screen = Gdk.Screen.get_default()
        style_context = Gtk.StyleContext()
        style_context.add_provider_for_screen(
            screen, css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    @log
    def _build_app_menu(self):
        action_entries = [
            ('about', self._about),
            ('quit', self.quit),
        ]

        for action, callback in action_entries:
            simple_action = Gio.SimpleAction.new(action, None)
            simple_action.connect('activate', callback)
            self.add_action(simple_action)

    @log
    def _about(self, action, param):
        def about_response(dialog, response):
            dialog.destroy()

        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Podcasts/AboutDialog.ui')
        about = builder.get_object('about_dialog')
        about.set_transient_for(self._window)
        about.connect("response", about_response)
        about.show()

    @log
    def do_startup(self):
        Gtk.Application.do_startup(self)
        Notify.init(_("Podcasts"))
        self._build_app_menu()

    @log
    def quit(self, action=None, param=None):
        self._window.destroy()

    def do_activate(self):
        if not self.tracker:
            self.tracker = PodcastTracker()

        if not self._window:
            self._window = Window(self)
            #if self._settings.get_value('notifications'):
                #self._notifications = NotificationManager(self._window.player)

        self._window.present()
