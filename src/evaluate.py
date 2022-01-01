from functools import lru_cache as cache_evaluation

from defs import *
from nnue import *
from position import *

@cache_evaluation(maxsize=0xFFFF)
def evaluate(pos: Position) -> Value:
    '''Main evaluation function.'''

    if pos.is_material_draw:
        return 0
    
    us = pos.side
    ours = pos.accumulator[us]        # Our accumulation
    theirs = pos.accumulator[not us]  # Their accumulation

    # Hidden layer forward propogation
    v = OUTPUT_BIAS * QUANTIZATION_PRECISION_IN + sum([
        + (ours[i] if ours[i] > 0 else 0) * HIDDEN_WEIGHTS[i]
        + (theirs[i] if theirs[i] > 0 else 0) * HIDDEN_WEIGHTS[i + N_HIDDEN]
        for i in range(N_HIDDEN)
    ])

    return Value(v / QUANTIZATION_PRECISION_IN / QUANTIZATION_PRECISION_OUT)
