import pygame
from pygame.locals import *
from twisted.internet import reactor


class IgnoreEvent(Exception):
    """ Stop processing this event
	
	Wait until `d` succeeds before processing any other events if `d` is given.
	"""

    def __init__(self, d=None):
        self.d = d


class State:
    events = {}  # handled when this state is active
    persistent_events = {}  # handled when this state is somewhere in the state stack
    stack = []

    def __init__(self):
        print("new state", self)
        State.stack.append(self)
        self.init_state_display()

    def quit(self):
        """leave this state"""
        print("leaving state", self)
        removedState = State.stack.pop()
        assert removedState == self, (
            "Can only leave active state. Tried to exit %s but %s is active"
            % (self, removedState)
        )
        if len(State.stack) > 0:
            State.stack[-1].init_state_display()
        # don't let events from the old state get to the new one
        pygame.event.clear()

    def is_active(self):
        if State.stack[-1] == self:
            return True
        else:
            return False

    def handle(self):
        """ Can return a deferred, in which case nothing happens until that deferred succeeds """
        pass

    def init_state_display(self):
        pass

    def on_event(event):
        """ Can return a deferred, in which case nothing happens until that deferred succeeds """
        # get top_state at the beginning, because must not change during the execution
        try:
            top_state = State.stack[-1]
        except IndexError:
            return
        try:
            # persistent events
            rev_stack = State.stack[:]
            rev_stack.reverse()
            for state in rev_stack:
                try:
                    handler = state.persistent_events[event.type]
                except KeyError:
                    continue
                handler(state, event)
            # events for active state
            try:
                handler = top_state.events[event.type]
            except KeyError:
                return
            return handler(top_state, event)
        except IgnoreEvent as e:
            return e.d

    on_event = staticmethod(on_event)


class MainState(State):
    """Handle all events which should always be handled"""

    def handle_keypress(self, event):
        if event.key == K_RETURN and event.mod == KMOD_LALT:
            pygame.display.toggle_fullscreen()
        if event.key == K_q and event.mod == KMOD_LMETA:
            reactor.stop()

    def handle(self):
        # quit if only MainState is left
        print("q")
        self.quit()

    def quit(self):
        State.quit(self)
        reactor.stop()

    def keepMusicRunning(self, event):
        import sound

        sound.play_music()

    from common import MUSICEVENT

    persistent_events = {
        KEYDOWN: handle_keypress,
        QUIT: (lambda self, event: self.quit),
        MUSICEVENT: keepMusicRunning,
    }


def runStateLoop():
    def stateLoop():
        event = pygame.event.poll()
        top_state = State.stack[-1]
        while event.type != NOEVENT:
            d = top_state.on_event(event)
            if d:
                d.addCallback(stateLoop)
                return
            event = pygame.event.poll()
        d = top_state.stack[-1].handle()
        if d:
            d.addCallback(stateLoop)
            return
        reactor.callLater(0.01, stateLoop)

    from twisted.internet.task import LoopingCall

    reactor.callWhenRunning(stateLoop)
    reactor.run()
