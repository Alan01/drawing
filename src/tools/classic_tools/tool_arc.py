# tool_arc.py

import cairo
from gi.repository import Gtk, Gdk

from .abstract_tool import AbstractAbstractTool
from .utilities import utilities_add_arrow_triangle

class ToolArc(AbstractAbstractTool):
	__gtype_name__ = 'ToolArc'

	def __init__(self, window, **kwargs):
		super().__init__('arc', _("Arc"), 'tool-arc-symbolic', window)
		self.use_size = True

		self.add_tool_action_enum('line_shape', 'round')
		self.add_tool_action_boolean('use_dashes', False)
		self.add_tool_action_boolean('is_arrow', False)
		self.add_tool_action_enum('cairo_operator', 'over')

		# Default values
		self.selected_shape_label = _("Round")
		self.selected_operator = cairo.Operator.OVER
		self.selected_end_id = cairo.LineCap.ROUND
		self.wait_points = (-1.0, -1.0, -1.0, -1.0)
		self.use_dashes = False
		self.use_arrow = False

	def set_active_shape(self):
		if self.get_option_value('line_shape') == 'square':
			self.selected_end_id = cairo.LineCap.BUTT
			self.selected_shape_label = _("Square")
		else:
			self.selected_end_id = cairo.LineCap.ROUND
			self.selected_shape_label = _("Round")

	def set_active_operator(self):
		state_as_string = self.get_option_value('cairo_operator')
		if state_as_string == 'difference':
			self.selected_operator = cairo.Operator.DIFFERENCE
			self.selected_operator_label = _("Difference")
		elif state_as_string == 'source':
			self.selected_operator = cairo.Operator.SOURCE
			self.selected_operator_label = _("Source color")
		elif state_as_string == 'clear':
			self.selected_operator = cairo.Operator.CLEAR
			self.selected_operator_label = _("Eraser")
		else:
			self.selected_operator = cairo.Operator.OVER
			self.selected_operator_label = _("Classic")

	def get_options_label(self):
		return _("Arc options")

	def get_edition_status(self): # TODO l'opérateur est important
		self.use_dashes = self.get_option_value('use_dashes')
		self.use_arrow = self.get_option_value('is_arrow')
		self.set_active_shape()
		self.set_active_operator()
		label = self.label + ' (' + self.selected_shape_label + ') '
		if self.use_arrow and self.use_dashes:
			label = label + ' - ' + _("Arrow") + ' - ' + _("With dashes")
		elif self.use_arrow:
			label = label + ' - ' + _("Arrow")
		elif self.use_dashes:
			label = label + ' - ' + _("With dashes")
		return label

	def give_back_control(self, preserve_selection):
		self.wait_points = (-1.0, -1.0, -1.0, -1.0)
		self.x_press = 0.0
		self.y_press = 0.0

	def on_press_on_area(self, event, surface, tool_width, left_color, right_color, event_x, event_y):
		self.x_press = event_x
		self.y_press = event_y
		self.tool_width = tool_width
		if event.button == 1:
			self.main_color = left_color
		if event.button == 3:
			self.main_color = right_color

	def on_motion_on_area(self, event, surface, event_x, event_y):
		self.restore_pixbuf()
		cairo_context = cairo.Context(self.get_surface())
		if self.wait_points == (-1.0, -1.0, -1.0, -1.0):
			cairo_context.move_to(self.x_press, self.y_press)
			cairo_context.line_to(event_x, event_y)
		else:
			cairo_context.move_to(self.wait_points[0], self.wait_points[1])
			cairo_context.curve_to(self.wait_points[2], self.wait_points[3], \
			                       self.x_press, self.y_press, event_x, event_y)
		self._path = cairo_context.copy_path()
		operation = self.build_operation(event_x, event_y)
		self.do_tool_operation(operation)

	def on_release_on_area(self, event, surface, event_x, event_y):
		if self.wait_points == (-1.0, -1.0, -1.0, -1.0):
			self.wait_points = (self.x_press, self.y_press, event_x, event_y)
			return
		else:
			self.restore_pixbuf()
			cairo_context = cairo.Context(self.get_surface())
			cairo_context.move_to(self.wait_points[0], self.wait_points[1])
			cairo_context.curve_to(self.wait_points[2], self.wait_points[3], \
			                       self.x_press, self.y_press, event_x, event_y)
			self.wait_points = (-1.0, -1.0, -1.0, -1.0)

		self._path = cairo_context.copy_path()
		operation = self.build_operation(event_x, event_y)
		self.apply_operation(operation)
		self.x_press = 0.0
		self.y_press = 0.0

	def build_operation(self, event_x, event_y):
		operation = {
			'tool_id': self.id,
			'rgba': self.main_color,
			'operator': self.selected_operator,
			'line_width': self.tool_width,
			'line_cap': self.selected_end_id,
			'use_dashes': self.use_dashes,
			'use_arrow': self.use_arrow,
			'path': self._path,
			'x_release': event_x,
			'y_release': event_y,
			'x_press': self.x_press,
			'y_press': self.y_press
		}
		return operation

	def do_tool_operation(self, operation):
		if operation['tool_id'] != self.id:
			return
		self.restore_pixbuf()
		cairo_context = cairo.Context(self.get_surface())
		cairo_context.set_operator(operation['operator'])
		cairo_context.set_line_cap(operation['line_cap'])
		#cairo_context.set_line_join(operation['line_join'])
		line_width = operation['line_width']
		cairo_context.set_line_width(line_width)
		rgba = operation['rgba']
		cairo_context.set_source_rgba(rgba.red, rgba.green, rgba.blue, rgba.alpha)
		if operation['use_dashes']:
			cairo_context.set_dash([2*line_width, 2*line_width])
		cairo_context.append_path(operation['path'])
		cairo_context.stroke()

		if operation['use_arrow']:
			x_press = operation['x_press']
			y_press = operation['y_press']
			x_release = operation['x_release']
			y_release = operation['y_release']
			utilities_add_arrow_triangle(cairo_context, x_release, y_release, \
			                                       x_press, y_press, line_width)

	############################################################################
################################################################################

