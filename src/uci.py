from defs import *
from perft import *
from search import *
from transposition import *

MOVE_OVERHEAD = 500       # 500ms move overhead
MIN_MOVE_TIME = 1000      # 1000ms minimum move time
MAX_MOVE_TIME = 120_000  # 2 minute maximum think time

def print_options():
    '''Prints available engine configurations.'''
    
    print('id name D-House 0.6')
    print('id author Alvin Peng')
    print('option name Clear Hash type button')
    print('option name Threads type spin default 1 min 1 max 4')
    print('uciok')

def parse_go(pos: Position, string: str, tt: Array) -> None:
    '''Parses UCI go command.'''

    tokens = string.split()
    side = pos.side
    depth = MAX_PLY
    moves_to_go = 25
    time_ms = 0

    # Moves to go
    if 'movestogo' in string:
        moves_to_go = int(tokens[tokens.index('movestogo') + 1])
    
    # Simple time management - take remaining time and divide by 
    # moves_to_go
    if side == WHITE:
        # White time remaining
        if 'wtime' in tokens:
            time_ms += int(tokens[tokens.index('wtime') + 1])
        # White increment
        if 'winc' in tokens:
            time_ms += int(tokens[tokens.index('winc') + 1])
    else:
        # Black time remaining
        if 'btime' in tokens:
            time_ms += int(tokens[tokens.index('btime') + 1])
        # Black increment
        if 'binc' in tokens:
            time_ms += int(tokens[tokens.index('binc') + 1])  
    time_ms = time_ms / moves_to_go

    # Search for a specified amound of time
    if 'movetime' in tokens:
        time_ms = int(tokens[tokens.index('movetime') + 1])

    # Search to specific depth (up to MAX_MOVE_TIME)
    if 'depth' in tokens:
        depth = int(tokens[tokens.index('depth') + 1])
        depth = min(depth, MAX_PLY)
        time_ms = MAX_MOVE_TIME

    time_ms = max(time_ms - MOVE_OVERHEAD, MIN_MOVE_TIME)

    # Search!
    search(pos=pos, depth=depth, time_ms=time_ms, tt=tt)
        
def uci_loop() -> None:

    pos = parse_fen()
    tt = make_tt()
    
    while True:
        string = input()

        if string == 'uci':
            print_options()

        if string == 'isready':
            print('readyok')

        if 'setoption name' in string:
            tokens = string.split()
            # Set thread count
            if 'setoption name Threads value' in string:
                set_thread_count(int(tokens[-1]))
            # Clear hash
            if 'setoption name Clear Hash' in string:
                tt = make_tt()

        if string == 'ucinewgame':
            pos = parse_fen()
            tt = make_tt()
            print('readyok')

        if 'position' in string:
            # Start position
            if 'startpos' in string:
                pos = parse_fen()
                string = string.replace('position startpos ', '')
                tokens = string.split()
            # Specific fen
            elif 'fen' in string:
                if 'move' not in string:
                    string += ' move'
                string = string.replace('position fen ', '')
                fen_end = string.index('move') 
                tokens = string.split()
                pos = parse_fen(string[:fen_end].replace('moves', ''))
            # Moves after given position
            tokens = string.split()
            for token in tokens:
                for move in gen_perft(pos):
                    if move_to_str(move) == token:
                        pos = do_move(pos, move)
                
        if 'go' in string:
            tokens = string.split()
            tokens.remove('go')
            # Perft test
            if tokens and tokens[0] == 'perft':
                perft_divide(pos, int(tokens[1]))
            # Search
            else:
                parse_go(pos, string, tt)

        # TODO
        if string == 'stop':
            pass

        if string == 'quit':
            quit()
