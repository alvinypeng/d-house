from defs import *

# Precalculated attack masks
with open('bitboard.txt', 'r') as file:
    exec(file.read())
    file.close()

def uint64(x: int) -> int:
    return x & 0xFFFFFFFFFFFFFFFF

def file_of(square: Square) -> int:
    return square & 7

def rank_of(square: Square) -> int:
    return square >> 3

def relative_rank(side: Color, rank: int) -> int:
    return (7 - rank) if side else rank

A_FILE = 0x101010101010101
B_FILE = 0x202020202020202
C_FILE = 0x404040404040404
D_FILE = 0x808080808080808
E_FILE = 0x1010101010101010
F_FILE = 0x2020202020202020
G_FILE = 0x4040404040404040
H_FILE = 0x8080808080808080

RANK_1 = 0xFF00000000000000
RANK_2 = 0x00FF000000000000
RANK_3 = 0x0000FF0000000000
RANK_4 = 0x000000FF00000000
RANK_5 = 0x00000000FF000000
RANK_6 = 0x0000000000FF0000
RANK_7 = 0x000000000000FF00
RANK_8 = 0x00000000000000FF

FILE_MASKS = A_FILE, B_FILE, C_FILE, D_FILE, E_FILE, F_FILE, G_FILE, H_FILE

RANK_MASKS = RANK_8, RANK_7, RANK_6, RANK_5, RANK_4, RANK_3, RANK_2, RANK_1

popcount_16 = [bin(x).count('1') for x in range(1 << 16)]

def bits(bb: Bitboard) -> int:
    return (+ popcount_16[(bb & 0x000000000000FFFF)]
            + popcount_16[(bb & 0x00000000FFFF0000) >> 16]
            + popcount_16[(bb & 0x0000FFFF00000000) >> 32]
            + popcount_16[(bb & 0xFFFF000000000000) >> 48])

def msb(bb: Bitboard) -> int:
    return bb.bit_length() - 1

def lsb(bb: Bitboard) -> int:
    if bb:
        return bits((bb & -bb) - 1)
    else:
        return -1

def bishop_attacks(square: Square, occupied: Bitboard) -> Bitboard:
    return BISHOP_ATTACKS[square][occupied & BISHOP_MASKS[square]]

def rook_attacks(square: Square, occupied: Bitboard) -> Bitboard:
    return ROOK_ATTACKS[square][occupied & ROOK_MASKS[square]]

def queen_attacks(square: Square, occupied: Bitboard) -> Bitboard:
    return (BISHOP_ATTACKS[square][occupied & BISHOP_MASKS[square]]
            | ROOK_ATTACKS[square][occupied & ROOK_MASKS[square]])

def print_bb(bb: Bitboard) -> None:
    print()
    for r in range(8):
        for f in range(8):
            sq = r * 8 + f
            if not f:
                print(' ' + str(8 - r) + ' ', end = '')
            print(' 1' if bb & (1 << sq) else ' 0', end = '')
        print()
    print('\n    a b c d e f g h')
    print('\n    Bitboard: ' + str(bb))
