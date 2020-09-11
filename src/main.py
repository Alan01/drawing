# main.py
#
# Copyright 2018-2020 Romain F. T.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import sys, gi
gi.require_version('Gtk', '3.0')
gi.require_version('PangoCairo', '1.0')
from gi.repository import Gtk, Gio, GLib, Gdk

from .window import DrawingWindow
from .preferences import DrawingPrefsWindow

APP_ID = 'com.github.maoschanz.drawing'
APP_PATH = '/com/github/maoschanz/drawing'
BUG_REPORT_URL = 'https://github.com/maoschanz/drawing/issues/new/choose'

def main(version):
	app = Application(version)
	return app.run(sys.argv)

################################################################################

class Application(Gtk.Application):
	shortcuts_window = None
	prefs_window = None

	############################################################################
	# Initialization ###########################################################

	def __init__(self, version):
		super().__init__(application_id=APP_ID,
		                 flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE)

		GLib.set_application_name(_("Drawing"))
		GLib.set_prgname(APP_ID)
		self._version = version
		self.has_tools_in_menubar = False

		self.connect('startup', self.on_startup)
		self.register(None)
		self.connect('activate', self.on_activate)
		self.connect('command-line', self.on_cli)

		self.add_main_option('version', b'v', GLib.OptionFlags.NONE,
		                     # Description of a command line option
		                     GLib.OptionArg.NONE, _("Show the app version"), None)
		self.add_main_option('new-window', b'n', GLib.OptionFlags.NONE,
		                     # Description of a command line option
		                     GLib.OptionArg.NONE, _("Open a new window"), None)
		self.add_main_option('new-tab', b't', GLib.OptionFlags.NONE,
		                     # Description of a command line option
		                     GLib.OptionArg.NONE, _("Open a new tab"), None)
		self.add_main_option('edit-clipboard', b'c', GLib.OptionFlags.NONE,
		             # Description of a command line option
		             GLib.OptionArg.NONE, _("Edit the clipboard content"), None)
		# TODO options pour le screenshot ?

		icon_theme = Gtk.IconTheme.get_default()
		icon_theme.add_resource_path(APP_PATH + '/icons')
		icon_theme.add_resource_path(APP_PATH + '/tools/icons')

	def on_startup(self, *args):
		"""Called only once, add app-wide menus and actions, and all accels."""
		self._build_actions()
		builder = Gtk.Builder.new_from_resource(APP_PATH + '/ui/app-menus.ui')
		menubar_model = builder.get_object('menu-bar')
		self.set_menubar(menubar_model)
		if self.prefers_app_menu():
			appmenu_model = builder.get_object('app-menu')
			self.set_app_menu(appmenu_model)

	def _build_actions(self):
		"""Add app-wide actions."""
		self.add_action_simple('new_window', self.on_new_window, ['<Ctrl>n'])
		self.add_action_simple('settings', self.on_prefs, None)
		if self.is_beta():
			self.add_action_simple('report_bug', self.on_report, None)
		self.add_action_simple('shortcuts', self.on_shortcuts, \
		                                         ['<Ctrl>question', '<Ctrl>F1'])
		self.add_action_simple('help', self.on_help_index, ['F1'])
		self.add_action_simple('help_main', self.on_help_main, None)
		self.add_action_simple('help_tools', self.on_help_tools, None)
		self.add_action_simple('help_canvas', self.on_help_canvas, None)
		self.add_action_simple('help_selection', self.on_help_selection, None)
		self.add_action_simple('about', self.on_about, ['<Shift>F1'])
		self.add_action_simple('quit', self.on_quit, ['<Ctrl>q'])
		self.add_action_enum('active-window', 0, self.change_active_win)

	# WINDOWS AND CLI MANAGEMENT ###############################################

	def change_active_win(self, *args):
		win_id = args[1].get_uint32()
		for window in self.get_windows():
			if not isinstance(window, Gtk.ApplicationWindow):
				continue
			elif window.get_id() is args[1].get_uint32():
				window.present()
		args[0].set_state( GLib.Variant('u', win_id) )

	def update_windows_menu_section(self, *args):
		# XXX trop appelée à mon goût
		section = self.get_menubar().get_item_link(6, \
		          Gio.MENU_LINK_SUBMENU).get_item_link(1, Gio.MENU_LINK_SECTION)
		section.remove_all()
		for window in self.get_windows():
			title = window.get_title()
			if not isinstance(window, Gtk.ApplicationWindow):
				continue
			elif title is None:
				continue
			else:
				detailed_name = 'app.active-window(uint32 ' + \
				                                      str(window.get_id()) + ')'
				try:
					title2 = title.split(' - ')
					title2 = title2[1] + ' - ' + title2[2]
				except Exception:
					title2 = title
				section.append(title2, detailed_name)

	def open_window_with_content(self, gfile, get_cb):
		"""Open a new window with an optional Gio.File as an argument. If get_cb
		is true, the Gio.File is ignored and the picture is built from the
		clipboard content."""
		win = DrawingWindow(application=self)
		win.present()
		win.init_window_content(gfile, get_cb) # this optimization has no effect
		# because of GLib unknown magic, but should be kept anyway because the
		# window is presented to the user regarless of loading errors, making
		# any issue in `init_window_content` very explicit, and more likely to
		# be reported.
		action = self.lookup_action('active-window')
		action.set_state( GLib.Variant('u', win.get_id()) )
		return win

	def on_activate(self, *args):
		"""I don't know if this is ever called from the 'activate' signal, but
		it's called by on_cli anyway."""
		win = self.props.active_window
		if not win:
			self.on_new_window()
		else:
			win.present()

	def on_cli(self, *args):
		"""Main handler, managing options and CLI arguments."""
		# This is the list of files given by the command line. If there is none,
		# this will be ['/app/bin/drawing'] which has a length of 1.
		arguments = args[1].get_arguments()

		# Possible options are 'version', 'new-window', and 'new-tab', in this
		# order: only one option can be applied, '-ntv' will be the same as '-v'.
		options = args[1].get_options_dict()

		if options.contains('version'):
			print(_("Drawing") + ' ' + self._version)
			if self.is_beta():
				print(_("This version isn't stable!"))
			print()
			print(_("Report bugs or ideas") + ' 👉️ ' + BUG_REPORT_URL)
		elif options.contains('edit-clipboard'):
			self.open_window_with_content(None, True)

		# If no file given as argument
		elif options.contains('new-window') and len(arguments) == 1:
			self.on_new_window()
		elif options.contains('new-tab') and len(arguments) == 1:
			win = self.props.active_window
			if not win:
				self.on_new_window()
			else:
				win.present()
				self.props.active_window.build_new_image()
		elif len(arguments) == 1:
			self.on_activate()

		elif options.contains('new-window'):
			self.on_new_window()
			for fpath in arguments:
				f = self._get_valid_file(args[1], fpath)
				if f is not None:
					self.open_window_with_content(f, False)
		else: # giving files without '-n' is equivalent to giving files with '-t'
			for fpath in arguments:
				f = self._get_valid_file(args[1], fpath)
				if f is not None:
					win = self.props.active_window
					if not win:
						self.open_window_with_content(f, False)
					else:
						win.present()
						self.props.active_window.build_new_tab(gfile=f)
		# I don't even know if i should return something
		return 0

	############################################################################
	# Actions callbacks ########################################################

	def on_new_window(self, *args):
		"""Action callback, opening a new window with an empty canvas."""
		return self.open_window_with_content(None, False)

	def on_report(self, *args):
		"""Action callback, opening a new issue on the github repo."""
		win = self.props.active_window
		Gtk.show_uri_on_window(win, BUG_REPORT_URL, Gdk.CURRENT_TIME)

	def on_shortcuts(self, *args):
		"""Action callback, showing the 'shortcuts' dialog."""
		if self.shortcuts_window is not None:
			self.shortcuts_window.destroy()
		builder = Gtk.Builder().new_from_resource(APP_PATH + '/ui/shortcuts.ui')
		self.shortcuts_window = builder.get_object('shortcuts')
		self.shortcuts_window.present()

	def on_prefs(self, *args):
		"""Action callback, showing the preferences window."""
		if self.prefs_window is not None:
			self.prefs_window.destroy()
		wants_csd = not 'ssd' in self.props.active_window.decorations
		self.prefs_window = DrawingPrefsWindow(self.is_beta(), wants_csd)
		self.prefs_window.present()

	def on_help_index(self, *args):
		"""Action callback, showing the index of user help manual."""
		self._show_help_page('')

	def on_help_main(self, *args):
		"""Action callback, showing the 'basic features' page of the user help
		manual."""
		self._show_help_page('/main_features')

	def on_help_tools(self, *args):
		"""Action callback, showing the 'tools' page of the user help manual."""
		self._show_help_page('/drawing_tools')

	def on_help_canvas(self, *args):
		"""Action callback, showing the 'canvas and selection tools' page of the
		user help manual."""
		self._show_help_page('/canvas_tools')

	def on_help_selection(self, *args):
		"""Action callback, showing the 'selection' page of the user
		help manual."""
		self._show_help_page('/selection_tools')

	def _show_help_page(self, suffix):
		win = self.props.active_window
		Gtk.show_uri_on_window(win, 'help:drawing' + suffix, Gdk.CURRENT_TIME)

	def on_about(self, *args):
		"""Action callback, showing the "about" dialog."""
		about_dialog = Gtk.AboutDialog(transient_for=self.props.active_window,
			copyright="© 2018-2020 Romain F. T.", authors=["Romain F. T."],
			# To tranlators: "translate" this by your name, it will be displayed
			# in the "about" dialog
			translator_credits=_("translator-credits"),
			# To translators: it's credits for the icons, consider that "Art
			# Libre" is proper name
			artists=["Tobias Bernard", "Romain F. T.",
			                       _("GNOME's \"Art Libre\" icon set authors")],
			comments=_("A drawing application for the GNOME desktop."),
			license_type=Gtk.License.GPL_3_0,
			logo_icon_name=APP_ID, version=str(self._version),
			website='https://maoschanz.github.io/drawing/',
			website_label=_("Official webpage"))
		about_dialog.run()
		about_dialog.destroy()

	def on_quit(self, *args):
		"""Action callback, quitting the entire app."""
		if self.shortcuts_window is not None:
			self.shortcuts_window.destroy()
		if self.prefs_window is not None:
			self.prefs_window.destroy()

		can_quit = True
		# Try (= ask confirmation) to quit the main window(s)
		main_windows = self.get_windows()
		for w in main_windows:
			if w.on_close():
				# User clicked on "cancel"
				can_quit = False
			else:
				w.close()
				w.destroy()

		# The expected behavior, but now theorically useless, since closing all
		# appwindows should quit automatically. It's too violent to be left
		# without a guard clause.
		if can_quit:
			self.quit()

	############################################################################
	# Utilities ################################################################

	def is_beta(self):
		"""Tells is the app version is even or odd, odd versions being considered
		as unstable versions. This affects available options and the style of
		the headerbar."""
		return (int(self._version.split('.')[1]) * 5) % 10 == 5

	def add_action_simple(self, action_name, callback, shortcuts):
		action = Gio.SimpleAction.new(action_name, None)
		action.connect('activate', callback)
		self.add_action(action)
		if shortcuts is not None:
			self.set_accels_for_action('app.' + action_name, shortcuts)

	def add_action_boolean(self, action_name, default, callback):
		action = Gio.SimpleAction().new_stateful(action_name, None, \
		                                      GLib.Variant.new_boolean(default))
		action.connect('change-state', callback)
		self.add_action(action)

	def add_action_enum(self, action_name, default, callback):
		# XXX attention, celle-ci fonctionne avec un int, pas une string
		action = Gio.SimpleAction().new_stateful(action_name, \
		             GLib.VariantType.new('u'), GLib.Variant('u', default))
		action.connect('change-state', callback)
		self.add_action(action)

	def _get_valid_file(self, app, path):
		"""Creates a GioFile object if the path corresponds to an image."""
		try:
			f = app.create_file_for_arg(path)
			if 'image/' in f.query_info('standard::*', \
				          Gio.FileQueryInfoFlags.NONE, None).get_content_type():
				return f
			else:
				return None # mainly when it's /app/bin/drawing
		except:
			err = _("Error opening this file. Did you mean %s ?")
			command = "\n\tflatpak run --file-forwarding {0} @@ {1} @@\n"
			# XXX can happen without flatpak
			command = command.format(APP_ID, path)
			print(err % command)
			return None

	############################################################################
################################################################################

