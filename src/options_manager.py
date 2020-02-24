# options_manager.py
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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import cairo
from gi.repository import GLib

class DrawingOptionsManager():
	__gtype_name__ = 'DrawingOptionsManager'

	def __init__(self, window):
		self.window = window
		self.cached_value1 = None
		self.cached_value2 = None

	def add_tool_option_boolean(self, name, default):
		if self.window.lookup_action(name) is not None:
			return
		self.window.add_action_boolean(name, default, self.boolean_callback)

	def add_tool_option_enum(self, name, default):
		if self.window.lookup_action(name) is not None:
			return
		self.window.add_action_enum(name, default, self.enum_callback)

	def get_value(self, name):
		if self.window.lookup_action(name) is None:
			return
		action = self.window.lookup_action(name)
		if action.get_state_type().dup_string() == 's':
			return action.get_state().get_string()
		else:
			return action.get_state()

	############################################################################

	def boolean_callback(self, *args):
		new_value = args[1].get_boolean()
		# current_value = args[0].get_state()
		args[0].set_state(GLib.Variant.new_boolean(new_value))
		self.window.set_picture_title()

	def enum_callback(self, *args):
		"""This callback is simple but can't handle both menuitems and
		radiobuttons. It is only good for menuitems and modelbuttons."""
		new_value = args[1].get_string()
		current_value = args[0].get_state().get_string()

		# No need to change the state if it's already as the user want.
		# Cases "m1 m1" or "b1 b1" or "b1 m1" or "m1 b1"
		if new_value == current_value:
			return

		# Actually change the state to the new value.
		args[0].set_state(GLib.Variant.new_string(new_value))
		self.window.set_picture_title()

	############################################################################
################################################################################
