import pygame
from pygame.locals import *
from numpy.oldnumeric import *
import common
from state import State, IgnoreEvent

class WidgetState(State):

	def __init__(self):
		State.__init__(self)
		self.widgets = []

	def handle(self):
		for w in self.widgets:
			w.draw()			
		common.update()

	def pass_to_widgets(self, event):
		if event.type == KEYDOWN and event.key == K_ESCAPE:
			self.quit()
			raise IgnoreEvent
		for w in self.widgets:
			w.handle_event(event)
	
	events = {
		MOUSEMOTION: pass_to_widgets,
		MOUSEBUTTONDOWN: pass_to_widgets,
		KEYDOWN: pass_to_widgets,
	}

class Widget(object):
	
	freeze_highlight = None
	hidden = False

	def __init__(self, pos, text=None, surfaces=None, on_click=None):
		State.stack[-1].widgets.append(self)
		self.on_click = on_click
		self.highlighted = False
		self.inactive = False
		if text != None:
			self.surfaces_from_text(text)
		elif surfaces != None:
			(self.normal_surface, self.highlight_surface) = surfaces
		else:
			raise Exception, "text or surfaces argument required"
		self.inactive_surface = None
		# negative positions are distance from screen edge
		pos = list(pos)
		for i in (0,1):
			if pos[i] == None:
				pos[i] = (common.screen.get_size()[i] - self.normal_surface.get_size()[i]) / 2
			elif pos[i] < 0:
				pos[i] = common.screen.get_size()[i] + pos[i] - self.normal_surface.get_size()[i]
		self.pos = pos
		
	def draw(self):
		if self.hidden:
			return
		# Widget is inactive
		if self.inactive:
			if not self.inactive_surface:
				# Create 50% transparent surface
				self.inactive_surface = self.normal_surface.convert_alpha()
				alpha = pygame.surfarray.pixels_alpha(self.inactive_surface)
				divide(alpha, array(2).astype(UInt8), alpha)
				del alpha
			common.blit(self.inactive_surface, self.pos)
			self.highlighted = False
			return
		
		# This widget can't be highlighted
		if not self.on_click:
			common.blit(self.normal_surface, self.pos)
			return
		
		# Is the mouse pointer above the widget?
		if not Widget.freeze_highlight:
			self.highlighted = True
			mouse_pos = pygame.mouse.get_pos()
			for i in (0,1):
				if mouse_pos[i] not in range(self.pos[i], self.pos[i] + self.normal_surface.get_size()[i]):
					self.highlighted = False
		else:
			self.highlighted = Widget.freeze_highlight == self
				
		if self.highlighted:
			surf = self.highlight_surface
		else:
			surf = self.normal_surface
		common.blit(surf, self.pos)

	def surfaces_from_text(self, text):
		self.normal_surface = common.font.render(str(text), True, (0,0,0))
		self.highlight_surface = common.font.render(str(text), True, (150,0,0))
		
	def handle_event(self, event):
		if not self.highlighted:
			return
		if (event.type == MOUSEBUTTONDOWN):
			self.on_click()
		

class Button(Widget):

	def __init__(self, text, pos, on_click):
		Widget.__init__(self, pos, text=text, on_click=on_click)


class Label(Widget):

	def __init__(self, text, pos):
		Widget.__init__(self, pos, text=text)


class SpinBox(Widget):

	up = map(lambda col: common.colorize(common.load_image("arrow.png", alpha=True), col), ( (0,0,0), (150,0,0) ))
	down = map(lambda surf: pygame.transform.flip(surf, False, True), up)
	_hidden = False

	def __init__(self, label, pos, choices, default=None, on_change=None):
		self._choices = list(choices)
		self.index = 0
		self.label = label
		if default != None:
			self.value = default
		if on_change:
			self.on_change = on_change

		Widget.__init__(self, pos, text='', on_click=None)

		# add arrows
		up_pos = (self.pos[0] - SpinBox.up[0].get_width(), self.pos[1])
		down_pos = (self.pos[0] - SpinBox.up[0].get_width(), self.pos[1] + self.normal_surface.get_height() - SpinBox.down[0].get_height())
		self.up_widget = Widget( up_pos, surfaces=SpinBox.up, on_click=lambda:self.change(-1))
		self.down_widget = Widget( down_pos, surfaces=SpinBox.down, on_click=lambda:self.change(1))

		self.update()

	def choices():
		def fget(self):
			return self._choices
		def fset(self, choices):
			selected_element = self._choices[self.index]
			self._choices = choices
			try:
				self.index = choices.index(selected_element)
			except ValueError:
				self.index = 0
			self.update()
		return locals()
	choices = property(**choices())

	def change(self, diff):
		self.index += diff
		if hasattr(self, 'on_change'):
			self.on_change()
		self.update()

	def update(self):
		self.surfaces_from_text(self.label + ': ' + str(self.choices[self.index]))
		self.up_widget.inactive = self.index == 0
		self.down_widget.inactive = self.index == len(self.choices) -1

	def value():
		def fset(self, value):
			try:
				self.index = self.choices.index(value)
			except NameError:
				raise NameError, "Could not find value in list of choices!"
		def fget(self):
			return self.choices[self.index]
		return locals()
	value = property(**value())

	def hidden():
		def fset(self, value):
			self._hidden = value
			self.up_widget.hidden = value
			self.down_widget.hidden = value
		def fget(self):
			return self._hidden
		return locals()
	hidden = property(**hidden())


class LineEdit(Widget):

	class EditState(WidgetState):
		def __init__(self, widget):
			WidgetState.__init__(self)
			self.widget = widget
			self.show_cursor = True
			pygame.time.set_timer(USEREVENT+1, 600)
			Widget.freeze_highlight = self.widget
			self.widget.update_text(self.show_cursor)

			# get widgets from previous State
			from state import State
			self.widgets = State.stack[-2].widgets

		def __del__(self):
			pygame.time.set_timer(USEREVENT+1, 0)
			Widget.freeze_highlight = None

		def blink(self, event):
			self.show_cursor = not self.show_cursor
			self.widget.update_text(self.show_cursor)

		def handleKeypress(self, event):
			if event.key == K_BACKSPACE:
				self.widget.value = self.widget.value[:-1]
			elif event.key in (K_RETURN, K_ESCAPE):
				self.quit()
			elif event.unicode:
				self.widget.value += event.unicode
			self.widget.update_text(self.show_cursor)

		events = {
			MOUSEBUTTONDOWN: lambda self, event: self.quit(),
			USEREVENT+1: blink,
			KEYDOWN: handleKeypress,
		}

	def __init__(self, label, pos, start_value):
		self.value = start_value
		self.label = label
		Widget.__init__(self, pos, text='', on_click=lambda: self.EditState(self))
		self.update_text()

	def update_text(self, show_cursor=False):
		if show_cursor:
			cursor = '|'
		else:
			cursor = ''
		self.surfaces_from_text(self.label + ': ' + str(self.value) + cursor)
	
	def get_value(self):
		return self.value

class KeyConfigButton(Widget):

	def get_key(self):
		event = pygame.event.wait()
		while event.type != KEYDOWN:
			event = pygame.event.wait()
		self.key_list[0] = event.key
		self.update_text()
		
	def update_text(self):
		self.surfaces_from_text(self.label + ': ' + pygame.key.name(self.key_list[0]))

	def __init__(self, label, pos, key_list):
		self.label = label
		self.key_list = key_list
		Widget.__init__(self, pos, text='', on_click=self.get_key)
		self.update_text()

