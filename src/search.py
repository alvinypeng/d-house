from math import log
from time import sleep, perf_counter
from multiprocessing import Array
from multiprocessing import Value as BestMove
from multiprocessing import Process as PseudoThread
import sys

from defs import *
from move import *
from history import *
from evaluate import *
from movepick import *
from position import *
from search_data import *
from transposition import *

MIN_THREADS = 1
MAX_THREADS = 4
THREADS = 1

WINDOW_SIZE = 12

UNKNOWN = 32257  # Some logic requires that UNKNOWN > CHECKMATE
CHECKMATE = 32256
MATE_BOUND = 30000
TB_WIN_BOUND = 20000

DELTA_CUTOFF = 150
SEE_PRUNE_CUTOFF = 20
SEE_PRUNE_CAPTURE_CUTOFF = 80

LMP = zeros(2, MAX_PLY)
LMR = zeros(MAX_PLY, 64)
STATIC_PRUNE = zeros(2, MAX_PLY)

# Ethereal's late move reduction table
for depth in range(1, MAX_PLY):
    for moves in range(1, 64):
        LMR[depth][moves] = int(0.8 + log(depth) * log(1.2 * moves) / 2.5)

# Initialize pruning tables 
for depth in range(MAX_PLY):
    STATIC_PRUNE[0][depth] = -SEE_PRUNE_CUTOFF * depth * depth
    STATIC_PRUNE[1][depth] = -SEE_PRUNE_CAPTURE_CUTOFF * depth

def set_thread_count(count: int = 1) -> None:
    '''Set the number of threads.'''
    global THREADS
    THREADS = min(MAX_THREADS, max(MIN_THREADS, count))

def quiescence(pos: Position, alpha: Value, beta: Value,
               data: SearchData, pv: list[Move]) -> Value:
    '''
    Quiescence search. Search until the position is quiet so when we
    finally evaluate the position, our evaluation is more reliable.
    '''

    tt = data.tt
    stack = data.stack
    
    child_pv = []

    data.nodes += 1

    # Draw
    if pos.is_material_draw or pos.is_repeated or pos.rule_50 > 99:
        return 0

    # Prevent overflow
    if stack.ply >= MAX_PLY:
        return evaluate(pos)

    # Check transposition table
    tte = tt_get(tt, pos)
    if tte:
        tt_value = tte.value

    # Transposition table is accurate
    if tte and tte.value != UNKNOWN:
        if (tte.bound is EXACT_BOUND
            or (tte.bound is LOWER_BOUND and tt_value >= beta)
            or (tte.bound is UPPER_BOUND and tt_value <= alpha)):
            return tt_value

    best_move = NULL_MOVE
    old_alpha = alpha
    best_value = -CHECKMATE + stack.ply

    # Evaluate position
    in_check = pos.in_check
    evaluation = UNKNOWN if in_check else evaluate(pos)
    stack[0].evaluation = evaluation

    # Can we use the transposition table value as a more accurate
    # evaluation of the position?
    if tte and tt_value != UNKNOWN:
        if tte.bound is (UPPER_BOUND, LOWER_BOUND)[tt_value > evaluation]:
            evaluation = tt_value

    # Standing pat
    if not in_check:
        if evaluation >= beta:
            return evaluation
        if evaluation > alpha:
            alpha = evaluation
        best_value = evaluation

    # Initialize move picker and SEE cutoff
    mp = MovePicker(pos, data)
    see_cutoff = max(0, alpha - evaluation - DELTA_CUTOFF)
    
    # Loop through only good tacticals
    for move in mp(quiescence=True, cutoff=see_cutoff):
        if not in_check and mp.phase > PLAY_GOOD_TACTICALS:
            break

        # Do the move
        stack[0].move = move
        stack.ply += 1
        value = -quiescence(do_move(pos, move), -beta, -alpha, data, child_pv)
        stack.ply -= 1

        # Regular quiescence search stuff
        if value > best_value:
            best_value = value
            best_move = move
            # Node is either pv or fail-high node
            if value > alpha:
                alpha = value
                # Update pv
                pv.clear()
                pv.append(move)
                pv += child_pv
            # Fail high
            if alpha >= beta:
                break

    # Store value in transposition table
    if best_value >= beta:
        bound = LOWER_BOUND
    elif best_value <= old_alpha:
        bound = UPPER_BOUND
    else:
        bound = EXACT_BOUND
    tt_put(tt, pos, best_value, 0, bound, best_move)

    return best_value
                
def negamax(pos: Position, alpha: Value, beta: Value, depth: int,
            cut_node: bool, data: SearchData, pv: list[Move]) -> Value:
    '''Searches a particular node of the game tree.'''

    tt = data.tt
    stack = data.stack
    
    child_pv = []
    
    is_root = not stack.ply
    is_pv = beta - alpha != 1
    
    old_alpha = alpha
    tt_value = UNKNOWN
    max_value = CHECKMATE
    value = best_value = -CHECKMATE

    tt_move = NULL_MOVE
    best_move = NULL_MOVE
    excluded = stack[0].excluded

    # Drop into quiescence search
    if depth <= 0:
        return quiescence(pos, alpha, beta, data, pv)

    data.nodes += 1

    if not is_root:
        # Draw
        if pos.is_material_draw or pos.is_repeated or pos.rule_50 > 99:
            return 2 - (data.nodes & 0x3)
        # Prevent overflow
        if stack.ply >= MAX_PLY:
            return evaluate(pos)
        # Mate distance pruning
        alpha = max(alpha, -CHECKMATE + stack.ply)
        beta = min(beta, CHECKMATE - stack.ply - 1)
        if alpha >= beta:
            return alpha

    # Check transposition table
    tte = None if excluded else tt_get(tt, pos)
    if tte:
        tt_move = tte.move
        tt_value = tte.value

    # Transposition table is accurate
    if not is_pv and tte and tte.depth >= depth and tte.value != UNKNOWN:
        if (tte.bound is EXACT_BOUND
            or (tte.bound is LOWER_BOUND and tt_value >= beta)
            or (tte.bound is UPPER_BOUND and tt_value <= alpha)):
            return tt_value

    # IIR
    if depth >= 4 and not tt_move and not excluded:
        depth -= 1

    # Get static evaluation
    in_check = pos.in_check
    if not excluded:
        evaluation = UNKNOWN if in_check else evaluate(pos)
        stack[0].evaluation = evaluation
    else:
        evaluation = stack[0].evaluation

    # Improving if evaluation has gone up
    improving = (not in_check and
                 stack.ply >= 2 and
                 (stack[-2].evaluation is UNKNOWN or
                  stack[-2].evaluation < stack[0].evaluation))

    # Reset excluded and killers next ply
    stack[1].excluded = NULL_MOVE
    stack[1].killers[0] = NULL_MOVE
    stack[1].killers[1] = NULL_MOVE

    # Init move picker
    mp = MovePicker(pos, data)

    if not is_pv and not in_check:

        # Can we use the transposition table value as a more accurate
        # evaluation of the position?
        if tte and tte.depth >= depth and tt_value != UNKNOWN:
            if tte.bound is (UPPER_BOUND, LOWER_BOUND)[tt_value > evaluation]:
                evaluation = tt_value

        # Reverse futility pruning
        if (depth < 7 and
            not excluded and
            evaluation < MATE_BOUND and
            evaluation - 50 * (depth - improving) - 10 >= beta):
            return evaluation

        # Null move pruning condition
        if (depth > 2 
            and not excluded
            and pos.has_non_pawn
            and stack[-1].move is not NULL_MOVE
            and evaluation - 10 * improving >= beta):
            
            # Reduction value
            r = min(depth, 4 + depth // 6 + min((evaluation - beta) // 256, 3))
            # Do null move reduced depth search
            stack[0].move = NULL_MOVE
            stack.ply += 1
            value = -negamax(do_null_move(pos), -beta, -beta + 1,
                             depth - r, not cut_node, data, child_pv)
            stack.ply -= 1
            # Cutoff if fails high
            if value >= beta:
                return beta

        # Prob cut condition
        prob_beta = beta + 110
        if (depth > 4 
            and abs(beta) < MATE_BOUND
            and not (tte and tte.depth >= depth - 3 and tt_value < prob_beta)):

            # Loop through tactical moves
            for move in mp(quiescence=True):
                if move is excluded:
                    continue
                # Do a quiescence search
                stack[0].move = move
                stack.ply += 1
                new_pos = do_move(pos, move)
                value = -quiescence(new_pos, -prob_beta,
                                    -prob_beta + 1, data, pv)
                # Quiescence search failed high so the move might be
                # good. Do a zero-window reduced depth search to make
                # sure it is.
                if value >= prob_beta:
                    value = -negamax(new_pos, -prob_beta, -prob_beta + 1,
                                     depth - 4, not cut_node, data, pv)
                stack.ply -= 1
                # Cutoff if fails high
                if value >= prob_beta:
                    return value

    tried_quiets = []
    tried_tacticals = []
    
    move_count = 0
    non_pruned_count = 0
    
    skip_quiets = False

    # Loop through moves
    for move in mp(tt_move=tt_move):
        if move is excluded:
            continue

        tactical = is_tactical(move)

        if (skip_quiets
            and not tactical
            and not in_check):
            continue

        move_count += 1
        
        if not tactical:
            counter_history = get_counter_history(data, move)
            quiet_history = get_quiet_history(pos, data, move)
            special_quiet = move in (mp.k1, mp.k2, mp.counter)
        else:
            counter_history = 0
            quiet_history = 0
            special_quiet = False

        if best_value > -MATE_BOUND:
            # Quiet history pruning
            if (depth < 9 
                and not tactical
                and not in_check
                and evaluation + 100 * depth <= alpha
                and quiet_history < 50000 // (1 + improving)):
                skip_quiets = True
            # Counter history pruning
            if (depth < 3
                and not tactical
                and not special_quiet
                and counter_history <= -4096):
                continue
            # Quiet SEE pruning    
            if (not tactical
                and see(pos, move) < STATIC_PRUNE[0][depth]):
                continue
            # Tactical SEE pruning
            if (tactical
                and mp.phase > PLAY_GOOD_TACTICALS
                and see(pos, move) < STATIC_PRUNE[1][depth]):
                continue

        non_pruned_count += 1
        
        if tactical:
            tried_tacticals.append(move)
        else:
            tried_quiets.append(move)

        extension = 0

        # Singular extension: extend if one move is better than the rest
        if (tte
            and depth > 6 
            and not is_root
            and not excluded
            and move is tt_move 
            and tte.depth >= depth - 3
            and tte.bound is LOWER_BOUND 
            and abs(tt_value) < MATE_BOUND):

            s_beta = max(tt_value - 3 * depth // 2, -CHECKMATE)
            s_depth = depth // 2 - 1

            stack[0].excluded = move
            value = negamax(pos, s_beta - 1, s_beta,
                            s_depth, cut_node, data, pv)
            stack[0].excluded = NULL_MOVE
            
            if value < s_beta:
                extension = 1 + (not is_pv and value < s_beta - 50)
            elif s_beta >= beta:
                return s_beta

        # History extension: extend if the tt has a good history score
        elif (tte
              and depth > 6 
              and not is_root 
              and move is tt_move 
              and quiet_history >= 98304):
            extension = 1

        # Recapture extension
        elif (is_pv
              and not is_root
              and is_capture(move)
              and is_capture(stack[-1].move)
              and move_end(move) == move_end(stack[-1].move)):
            extension = 1

        # Do move
        stack[0].move = move
        stack.ply += 1
        new_pos = do_move(pos, move)

        # Apply extensions
        new_depth = depth + max(extension, (in_check and depth < 7))
        
        # LMR
        r = 1
        if depth > 2 and non_pruned_count > 1:
            r = LMR[min(depth, 63)][min(non_pruned_count, 63)]
            # Quiet reduction
            if not tactical:
                if not is_pv:
                    r += 1
                if not improving:
                    r += 1
                if special_quiet:
                    r -= 2
                if cut_node:
                    r += 1
                if new_pos.in_check:
                    r += 1
                r -= quiet_history // 20480
            # Tactical reduction
            else:
                th = get_tactical_history(pos, data, move)
                r = 1 - 4 * th // (abs(th) + 24576)
                r += cut_node
            # Make sure we don't reduce or extend too much
            r = min(depth - 1, max(r, 1))

        # PVS
        if is_pv and non_pruned_count == 1:
            value = -negamax(new_pos, -beta, -alpha,
                             new_depth - 1, False, data, child_pv)
        else:
            # Zero window search with reduction
            value = -negamax(new_pos, -alpha - 1, -alpha,
                             new_depth - r, True, data, child_pv)
            # Failed high on reduced search, try again with zero window
            # search but without reduction
            if value > alpha and r != 1:
                value = -negamax(new_pos, -alpha - 1, -alpha,
                                 new_depth - 1, not cut_node, data, child_pv)
            # Failed high again, do a full window search
            if value > alpha and (is_root or value < beta):
                value = -negamax(new_pos, -beta, -alpha,
                                 new_depth - 1, False, data, child_pv)
                
        stack.ply -= 1

        # Regular negamax stuff
        if value > best_value:
            best_move = move
            best_value = value
            # Node is either pv or fail-high node
            if value > alpha:
                alpha = value
                # Update pv
                pv.clear()
                pv.append(move)
                pv += child_pv
            # We failed high
            if alpha >= beta:
                update_histories(pos, data, move,
                                 depth + (best_value > beta + 100),
                                 tried_tacticals, tried_quiets)
                break

    # Checkmate/Draw detection
    if move_count == 0:
        return -CHECKMATE + stack.ply if in_check else 0

    # Make sure best value isn't out of bounds
    best_value = min(best_value, max_value)

    # Store value in transposition table       
    if not excluded:
        if best_value >= beta:
            bound = LOWER_BOUND
        elif best_value <= old_alpha:
            bound = UPPER_BOUND
        else:
            bound = EXACT_BOUND
        tt_put(tt, pos, best_value, depth, bound, best_move)

    return best_value 

def aspiration_window(pos: Position, value: Value,
                      depth: int, data: SearchData, pv: list[Move]) -> None:
    '''
    Searches at d - 1 can be a good estimate for a search at depth d.
    So, we can perform searches with a reduced window size rather than
    from -CHECKMATE to CHECKMATE to produce more cutoffs.
    '''

    # Shrink window after the first few iterations
    if depth > 6 and abs(value) <= 1000:
        alpha = max(value - WINDOW_SIZE, -CHECKMATE)
        beta = min(value + WINDOW_SIZE, CHECKMATE)
        delta = WINDOW_SIZE
    else:
        alpha = -CHECKMATE
        beta = CHECKMATE
        delta = CHECKMATE

    while True:
        value = negamax(pos, alpha, beta, depth, False, data, pv)
        # Failed low so reduce lower bound and search again
        if value <= alpha:
            alpha = max(alpha - delta, -CHECKMATE)
            beta = (alpha + beta) // 2 
        # Failed high so increase upper bound and search again
        elif value >= beta:
            beta = min(beta + delta, CHECKMATE)
            depth -= abs(value) < TB_WIN_BOUND
        # Finish searching this depth because the value is ok
        else:
            break
        # Increase window size because the search failed
        delta += delta // 2

    return value

def iterative_deepening(pos: Position, depth: int, thread_no: int,
                        tt: Array, node_counts: Array, best: BestMove) -> None:
    '''
    We don't know how long a search at a given depth will take. So, we
    perform a search to depth 1, then 2 and so on until max depth is
    reached or time is up.
    '''

    value = 0
    depth = min(depth, MAX_PLY)
    data = SearchData(tt=tt)
    start = perf_counter()

    # Iterative deepening
    for d in range(1, depth + 1):
        pv = []
        value = aspiration_window(pos, value, d, data, pv)

        # Update best move
        if thread_no == 0:
            best.value = pv[0]
            
        # Update node count
        node_counts[thread_no] += data.nodes
        nodes = sum(node_counts)
        
        # Score
        if value >= MATE_BOUND:
            score_str = f'score mate {int((CHECKMATE - value + 1) // 2)} '
        elif value <= -MATE_BOUND:
            score_str = f'score mate {int(-(CHECKMATE + value) // 2)} '
        else:
            score_str = f'score cp {value} '
            
        # Time
        time_elapsed = perf_counter() - start

        # Print info
        if thread_no == 0:
            info = f'info depth {d} '
            info += score_str
            info += (
                f'nodes {nodes} '
                f'time {round(time_elapsed * 1e3)} '
                f'pv '
            )
            # PV
            for move in pv:
                info += f'{move_to_str(move)} '
            print(info)
            sys.stdout.flush()

def search(pos: Position, depth: int, time_ms: int, tt: Array) -> None:

    start = perf_counter()
    time_s = time_ms / 1000

    best = BestMove('i', next(gen_perft(pos)))
    node_counts = Array('i', THREADS)

    # Initialize threads
    threads = []
    for thread_no in range(THREADS):
        thread = PseudoThread(target=iterative_deepening,
                              args=(pos, depth, thread_no,
                                    tt, node_counts, best))
        threads.append(thread)

    # Start threads
    for thread in reversed(threads):
        thread.start()

    while perf_counter() - start <= time_s:
        # If all processes are done, we break
        if not any([t.is_alive() for t in threads]):
            break
        # Sleep to avoid hogging cpu
        sleep(0.1)
    else:
        for thread in reversed(threads):
            thread.terminate()
            thread.join()

    # Print best move
    print(f'bestmove {move_to_str(best.value)}')
