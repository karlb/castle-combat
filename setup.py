from distutils.core import setup
#setup(name="castle-combat",
#      version="0.8.0-alpha1",
#      py_modules=["main", "menu", "widget", "player", "buildplayer", "placeplayer", "battleplayer", "selectplayer", "game", "gamephases", "cannon", "field"])
#      py_modules=["main"])

#import glob
#from os.path import basename, join
#import os

#os.mkdir('src')
#for file in glob.glob('../../src/*.py'):
#	print file, "src/"+basename(file)
#	os.symlink(file, join('src', basename(file)) )
	  
setup(name="castle-combat",
      version="0.8.1",
      description="Multiplayer action/strategy game",
      author="Karl Bartel",
      author_email="karlb@gmx.net",
      url="http://www.linux-games.com",
#      package_dir={'': 'src'},
#      packages=['src']
      packages=["src"],
      scripts=["castle-combat.py"],
      py_modules=["castle-combat"]
#      py_modules=["src/main", "src/menu", "src/widget", "src/player", "src/buildplayer", "src/placeplayer", "src/battleplayer", "src/selectplayer", "src/game", "src/gamephases", "src/cannon", "src/field", "src/common", "src/config", "src/client", "server"]
     )

#os.rmdir('src')

