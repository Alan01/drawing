# tool_polygon.py

from gi.repository import Gtk, Gdk
import cairo

from .abstract_tool import AbstractAbstractTool
from .utilities import utilities_generic_shape_tool_operation

class ToolPolygon(AbstractAbstractTool):
	__gtype_name__ = 'ToolPolygon'

	def __init__(self, window, **kwargs):
		super().__init__('polygon', _("Polygon"), 'tool-polygon-symbolic', window)
		self.use_size = True

		(self.x_press, self.y_press) = (-1.0, -1.0)
		(self.past_x, self.past_y) = (-1.0, -1.0)
		self.selected_style_id = 'secondary'
		self.selected_join_id = cairo.LineJoin.MITER

		self.add_tool_action_enum('filling_style', 'secondary')

	def set_filling_style(self):
		state_as_string = self.get_option_value('filling_style')
		self.selected_style_id = state_as_string

	def get_options_label(self):
		return _("Polygon options")

	def get_edition_status(self):
		self.set_filling_style()
		label = self.label + ' - ' + _("Click on the shape's first point to close it.")
		return label

	def give_back_control(self, preserve_selection):
		self.restore_pixbuf()
		(self.x_press, self.y_press) = (-1.0, -1.0)
		(self.past_x, self.past_y) = (-1.0, -1.0)

	def draw_polygon(self, event_x, event_y, is_preview):
		cairo_context = cairo.Context(self.get_surface())
		cairo_context.set_line_width(self.tool_width)

		if self.past_x == -1.0:
			self.init_polygon(cairo_context)
		else:
			cairo_context.append_path(self._path)

		if is_preview:
			self.preview_polygon(cairo_context, event_x, event_y)
			return False

		if self.past_x != -1.0 and self.past_y != -1.0 \
		and (max(event_x, self.past_x) - min(event_x, self.past_x) < self.tool_width) \
		and (max(event_y, self.past_y) - min(event_y, self.past_y) < self.tool_width):
			cairo_context.close_path()
			self._path = cairo_context.copy_path()
			return True
		else:
			self.continue_polygon(cairo_context, event_x, event_y)
			return False

	def init_polygon(self, cairo_context): # TODO simplfiable depuis que c'est split en 2 outils
		(self.past_x, self.past_y) = (self.x_press, self.y_press)
		cairo_context.move_to(self.x_press, self.y_press)
		self._path = cairo_context.copy_path()

	def continue_polygon(self, cairo_context, x, y):
		cairo_context.set_line_width(self.tool_width)
		cairo_context.set_source_rgba(self.main_color.red, self.main_color.green, \
			self.main_color.blue, self.main_color.alpha)
		cairo_context.line_to(x, y)
		cairo_context.stroke_preserve() # draw the line without closing the path
		self._path = cairo_context.copy_path()
		self.non_destructive_show_modif()

	def preview_polygon(self, cairo_context, x, y):
		cairo_context.line_to(x, y)
		cairo_context.close_path()
		operation = self.build_operation(cairo_context.copy_path())
		self.do_tool_operation(operation)

	def on_press_on_area(self, event, surface, tool_width, left_color, right_color, event_x, event_y):
		self.x_press = event_x
		self.y_press = event_y
		self.tool_width = tool_width
		if event.button == 3:
			self.main_color = right_color
			self.secondary_color = left_color
		else:
			self.main_color = left_color
			self.secondary_color = right_color

	def on_motion_on_area(self, event, surface, event_x, event_y):
		self.restore_pixbuf()
		self.draw_polygon(event_x, event_y, True)

	def on_release_on_area(self, event, surface, event_x, event_y):
		self.restore_pixbuf()
		finished = self.draw_polygon(event_x, event_y, False)
		if finished:
			operation = self.build_operation(self._path)
			self.apply_operation(operation)
			(self.x_press, self.y_press) = (-1.0, -1.0)
			(self.past_x, self.past_y) = (-1.0, -1.0)

	def build_operation(self, cairo_path):
		operation = {
			'tool_id': self.id,
			'rgba_main': self.main_color,
			'rgba_secd': self.secondary_color,
			'operator': cairo.Operator.OVER,
			'line_join': self.selected_join_id,
			'line_width': self.tool_width,
			'filling': self.selected_style_id,
			'path': cairo_path
		}
		return operation

	def do_tool_operation(self, operation): # TODO choix du line join ?
		if operation['tool_id'] != self.id:
			return
		self.restore_pixbuf()
		cairo_context = cairo.Context(self.get_surface())
		utilities_generic_shape_tool_operation(cairo_context, operation)

