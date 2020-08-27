# tool_paint.py

import cairo
from gi.repository import Gtk, Gdk, GdkPixbuf

from .abstract_tool import AbstractAbstractTool
from .utilities import utilities_get_magic_path
from .utilities import utilities_get_rgb_for_xy

class ToolPaint(AbstractAbstractTool):
	__gtype_name__ = 'ToolPaint'

	def __init__(self, window, **kwargs):
		super().__init__('paint', _("Paint"), 'tool-paint-symbolic', window)
		self.new_color = None
		self.magic_path = None
		self.use_size = False
		self.add_tool_action_enum('paint_algo', 'fill')

	def get_options_label(self):
		return _("Painting options")

	def get_edition_status(self):
		if self.get_option_value('paint_algo') == 'clipping':
			return _("Click on an area to replace its color by transparency")
		else:
			return self.label

	def on_press_on_area(self, event, surface, tool_width, left_color, right_color, event_x, event_y):
		if event.button == 1:
			self.new_color = left_color
		if event.button == 3:
			self.new_color = right_color

	def on_release_on_area(self, event, surface, event_x, event_y):
		# Guard clause: we can't paint outside of the surface
		if event_x < 0 or event_x > surface.get_width() \
		or event_y < 0 or event_y > surface.get_height():
			return

		(x, y) = (int(event_x), int(event_y))
		self.old_color = utilities_get_rgb_for_xy(surface, x, y)

		if self.get_option_value('paint_algo') == 'fill':
			self.magic_path = utilities_get_magic_path(surface, x, y, self.window, 1)
		elif self.get_option_value('paint_algo') == 'replace':
			self.magic_path = utilities_get_magic_path(surface, x, y, self.window, 2)
		else:
			pass # == 'clipping'

		operation = self.build_operation()
		self.apply_operation(operation)

	############################################################################

	def build_operation(self):
		operation = {
			'tool_id': self.id,
			'algo': self.get_option_value('paint_algo'),
			'rgba': self.new_color,
			'old_rgb': self.old_color,
			'path': self.magic_path
		}
		return operation

	def do_tool_operation(self, operation):
		if operation['tool_id'] != self.id:
			return
		self.restore_pixbuf()

		if operation['algo'] == 'replace':
			self._op_replace(operation)
		elif operation['algo'] == 'fill':
			self._op_fill(operation)
		else: # == 'clipping'
			self._op_clipping(operation)

	############################################################################

	def _op_replace(self, operation):
		"""Algorithmically less ugly than `_op_fill`, but doesn't handle (semi-)
		transparent colors correctly, even outside of the targeted area."""
		# FIXME
		if operation['path'] is None:
			return
		surf = self.get_surface()
		cairo_context = cairo.Context(surf)
		rgba = operation['rgba']
		old_rgb = operation['old_rgb']
		cairo_context.set_source_rgba(255, 255, 255, 1.0)
		cairo_context.append_path(operation['path'])
		cairo_context.set_operator(cairo.Operator.DEST_IN)
		cairo_context.fill_preserve()

		pixbuf1 = Gdk.pixbuf_get_from_surface(surf, 0, 0, \
		                                    surf.get_width(), surf.get_height())
		self.get_image().set_temp_pixbuf(pixbuf1)

		tolerance = 10 # XXX
		i = -1 * tolerance
		while i < tolerance:
			red = max(0, old_rgb[0]+i)
			green = max(0, old_rgb[1]+i)
			blue = max(0, old_rgb[2]+i)
			red = int( min(255, red) )
			green = int( min(255, green) )
			blue = int( min(255, blue) )
			self.replace_temp_with_alpha(red, green, blue)
			i = i+1
		self.restore_pixbuf()
		cairo_context2 = cairo.Context(self.get_surface())

		cairo_context2.append_path(operation['path'])
		cairo_context2.set_operator(cairo.Operator.CLEAR)
		cairo_context2.set_source_rgba(255, 255, 255, 1.0)
		cairo_context2.fill()
		cairo_context2.set_operator(cairo.Operator.OVER)

		Gdk.cairo_set_source_pixbuf(cairo_context2, \
		                               self.get_image().temp_pixbuf, 0, 0)
		cairo_context2.append_path(operation['path'])
		cairo_context2.paint()
		self.non_destructive_show_modif()
		cairo_context2.set_operator(cairo.Operator.DEST_OVER)
		cairo_context2.set_source_rgba(rgba.red, rgba.green, rgba.blue, rgba.alpha)
		cairo_context2.paint()

	def _op_fill(self, operation):
		"""Simple but ugly, and it's relying on the precision of the provided
		path whose creation is based on shitty heurisctics."""
		if operation['path'] is None:
			return
		cairo_context = cairo.Context(self.get_surface())
		rgba = operation['rgba']
		cairo_context.set_source_rgba(rgba.red, rgba.green, rgba.blue, rgba.alpha)
		cairo_context.append_path(operation['path'])
		cairo_context.fill()

	def _op_clipping(self, operation):
		"""Replace the color with transparency by adding an alpha channel."""
		old_rgba = operation['old_rgb']
		r0 = old_rgba[0]
		g0 = old_rgba[1]
		b0 = old_rgba[2]
		# XXX and the alpha channel ? pas l'air possible en fait
		margin = 0 # TODO as an option ? is not elegant but is powerful
		self._clip_red(margin, r0, g0, b0)
		self.restore_pixbuf()
		self.non_destructive_show_modif()

	def _clip_red(self, margin, r0, g0, b0):
		for i in range(-1 * margin, margin + 1):
			r = r0 + i
			if r <= 255 and r >= 0:
				self._clip_green(margin, r, g0, b0)

	def _clip_green(self, margin, r, g0, b0):
		for i in range(-1 * margin, margin + 1):
			g = g0 + i
			if g <= 255 and g >= 0:
				self._clip_blue(margin, r, g, b0)

	def _clip_blue(self, margin, r, g, b0):
		for i in range(-1 * margin, margin + 1):
			b = b0 + i
			if b <= 255 and b >= 0:
				self._replace_main_with_alpha(r, g, b)

	def _replace_main_with_alpha(self, red, green, blue):
		new_pixbuf = self.get_main_pixbuf().add_alpha(True, red, green, blue)
		self.get_image().set_main_pixbuf(new_pixbuf)

	def replace_temp_with_alpha(self, red, green, blue):
		pixbuf1 = self.get_image().temp_pixbuf.add_alpha(True, red, green, blue)
		self.get_image().set_temp_pixbuf(pixbuf1)

	############################################################################
################################################################################
