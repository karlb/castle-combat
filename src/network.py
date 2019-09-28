from twisted.spread import pb
from twisted.internet import defer
import common

class ServerObject(pb.Cacheable, pb.Referenceable):
	def __init__(self, *args, **kwargs):
		# Call superclass (this can be done with 'super', after switching to new-style classes)
		superclass = [cls for cls in self.__class__.__bases__ if cls not in (pb.Cacheable, pb.Referenceable, ServerObject)][0]
		superclass.__init__(self, *args, **kwargs)
		self.observers = []
	def getStateToCacheAndObserveFor(self, perspective, observer):
		self.observers.append(observer)
		state = self.get_state()
		state['remote_ref'] = pb.AsReferenceable(self)
		return state

class ClientObject(pb.RemoteCache):
	def __init__(self):
		pass
	def setCopyableState(self, state):
		self.set_state(state)
	def set_state(self, state):
		self.__dict__ = state


def delegate_and_call_observers(cls, to_class, method_names):
	"""Adds wrapper methods around the given methods to inform network clients

	This function should be called on a ServerObject class
	The added code looks like this:
	def METHOD_NAME(self, *args, **kwargs):
		try:
			TO_CLASS.METHOD_NAME(self, *args, **kwargs)
		except common.ActionNotPossible:
			return
		for o in self.observers: o.callRemote('METHOD_NAME', *args, **kwargs)
	local_METHOD_NAME = METHOD_NAME
	remote_METHOD_NAME = METHOD_NAME
	"""
	def delegate_and_call(method_name, self, *args, **kwargs):
		try:
			getattr(to_class, method_name)(self, *args, **kwargs)
		except common.ActionNotPossible:
			return
		return defer.DeferredList([
                    o.callRemote(method_name, *args, **kwargs)
                    for o in self.observers
                ])
	def create_method(method_name):
		return lambda *args, **kwargs: delegate_and_call(method_name, *args, **kwargs)
		
	for method_name in method_names:
		setattr(cls, 'local_' + method_name, getattr(cls, method_name))
		setattr(cls, method_name, create_method(method_name))
		setattr(cls, 'remote_' + method_name, getattr(cls, method_name))
	
def observe_and_delegate(cls, to_class, method_names):
	"""Adds wrapper methods around the given methods to handle networking

	This function should be called on a ClientObject class
	The added code looks like this:
	local_METHOD_NAME = METHOD_NAME
	observe_METHOD_NAME = TO_CLASS.METHOD_NAME
	def METHOD_NAME(self, *args, **kwargs):
		self.remote_ref.callRemote('METHOD_NAME', *args, **kwargs)
	"""
	def call_remote(method_name, self, *args, **kwargs):
		self.remote_ref.callRemote(method_name, *args, **kwargs)
	def create_method(method_name):
		return lambda *args, **kwargs: call_remote(method_name, *args, **kwargs)
		
	for method_name in method_names:
		setattr(cls, 'local_' + method_name, getattr(cls, method_name))
		setattr(cls, 'observe_' + method_name, getattr(to_class, method_name))
		setattr(cls, method_name, create_method(method_name))

def networkify(cacheable, remote_cache, implementation, method_names):
	"""Wraps methods in a Cacheable/RemoteCache class pair to make a sequence of methods network aware

	The first three parameter are classes, the methods_names parameter should be a list of methods_names.
	"""
	delegate_and_call_observers(cacheable, implementation, method_names)
	observe_and_delegate(remote_cache, implementation, method_names)
	pb.setUnjellyableForClass(cacheable, remote_cache)
