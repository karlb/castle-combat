import pygame
from pygame.locals import *
import common

def init():
	pygame.init()
	common.init()

def get_opts():
	import getopt, sys

	is_server = False

	try:
		opts, args = getopt.getopt(sys.argv[1:], "s", ["server"])
	except getopt.GetoptError:
		print "Wrong parameter. Sorry."
		sys.exit(2)
	output = None
	verbose = False
	for opt, arg in opts:
		if opt == "-s":
			is_server = True

	return (is_server)

def main():
#	(is_server) = get_opts()
#	import sys
#	print sys.argv
	import config
	config.load()
	init()

	from state import MainState, runStateLoop
	MainState()
	
	from menu import MenuState
	MenuState()

	runStateLoop()
	
	config.save()

if __name__ == '__main__':
	main()

