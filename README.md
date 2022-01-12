# Introduction
D-house is a UCI-compliant chess engine written in Python.

# Run it
D-house only uses the Python standard library, so you only need a working version of Python 3.9 or above. 
However, you may need to install a program such as 
[pyinstaller](https://pypi.org/project/pyinstaller/), or [py2exe](https://pypi.org/project/py2exe/) if you wish to create an executable. 

Currently only tested on Windows but may work on other operating systems.

# Performance
D-house appears to play better single-core rather than multi-core for some reason.

Playing strength is mediocre in fast time controls, but scales up in medium to long time controls (e.g. 40/15 and 40/40).

# Influences
The creation of this chess engine would not have been possible without the following resources:
* [Chess Programming Wiki](https://www.chessprogramming.org/Main_Page)<br/>
* [Andy Grant - Ethereal](https://github.com/AndyGrant/Ethereal)<br/>
* [Daniel Inführ - Gigantua](https://github.com/Gigantua/Gigantua)<br/>
* [Jay Honnold - Berserk](https://github.com/jhonnold/berserk)<br/>
* [Maksim Korzh - BBC](https://github.com/maksimKorzh/bbc)<br/>
* [Stockfish Team - Stockfish](https://github.com/official-stockfish/Stockfish)<br/>
* [Terje Kirstihagen - Weiss](https://github.com/TerjeKir/weiss)<br/>
* [Thomas Ahle - Sunfish](https://github.com/thomasahle/sunfish)<br/>
