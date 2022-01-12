# Introduction
D-house is a UCI-compliant chess engine written in Python.

# Run it
D-house only uses the Python standard library, so you only need a working version of Python 3.9 or above.
However, you may need to install a program such as 
[pyinstaller](https://pypi.org/project/pyinstaller/), or [py2exe](https://pypi.org/project/py2exe/) if you wish to create an executable. D-house currently plays best on CPython version 3.9.

Currently only tested on Windows but may work on other operating systems.

# Performance
D-house appears to play better single-core rather than multi-core for some reason.

Playing strength is mediocre in fast time control blitz, but scales up well in medium to long time control classical games (e.g. 40/15 and 40/40). In the testing game shown below, D-house (black) wins with a French Defense against [MadChess 3.0](http://ccrl.chessdom.com/ccrl/4040/cgi/engine_details.cgi?match_length=30&each_game=1&print=Details&each_game=1&eng=MadChess%203.0%2064-bit#MadChess_3_0_64-bit) (white) in a 40/15 game.

<img src="images/MadChess 3.0 vs D-house 0.6.gif" width="300" height="300">

**MadChess 3.0 vs D-house 0.6, 0-1** ([PGN](images/MadChess%203.0%20vs%20D-house%200.6.pgn))

# Influences
The creation of this chess engine would not have been possible without the following resources:
* [Chess Programming Wiki](https://www.chessprogramming.org/Main_Page)<br/>
* [Andy Grant - Ethereal](https://github.com/AndyGrant/Ethereal)<br/>
* [Daniel Inführ - Gigantua](https://github.com/Gigantua/Gigantua)<br/>
* [Erik Madsen - MadChess](https://www.madchess.net/)<br/>
* [Jay Honnold - Berserk](https://github.com/jhonnold/berserk)<br/>
* [Maksim Korzh - BBC](https://github.com/maksimKorzh/bbc)<br/>
* [Stockfish Team - Stockfish](https://github.com/official-stockfish/Stockfish)<br/>
* [Terje Kirstihagen - Weiss](https://github.com/TerjeKir/weiss)<br/>
* [Thomas Ahle - Sunfish](https://github.com/thomasahle/sunfish)<br/>
