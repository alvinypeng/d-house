from defs import *

# Network architecture used by Berserk 6
N_FEATURES = 768
N_HIDDEN = 256
N_OUTPUT = 1

QUANTIZATION_PRECISION_IN = 32
QUANTIZATION_PRECISION_OUT = 512

# Network weights & biases
with open('nnue.txt', 'r') as file:
    exec(file.read())
    file.close()

# Feature index indexed by [color][piece][square]
FEATURE_INDEX = zeros(2, 14, 64)

# Initialize FEATURE_INDEX
for color in (WHITE, BLACK):
    for piece in PIECES[2:]:
        for square in range(64):
            index = (64 * ((piece // 2 - 1) + 6 * (piece & 0x1 != color))
                     + square ^ (0x38 if color is WHITE else 0)) * N_HIDDEN
            FEATURE_INDEX[color][piece][square] = index
