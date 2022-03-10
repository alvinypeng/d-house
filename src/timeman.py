from time import perf_counter

from defs import *
from pseudothread import SharedInt

MOVE_OVERHEAD = 100 * 1e-3

class TimeManager:

    def __init__(self, search_flag: SharedInt,
                 movetime: int, time: int, inc: int, movestogo: int) -> None:

        self.depth = 0
        self.start = perf_counter()

        self.search_flag = search_flag
        self.movetime = movetime
        self.time = time
        self.inc = inc
        self.movestogo = min(40, movestogo) if movestogo else 30
        
        if self.movetime:
            self.alloc = self.movetime
        elif self.time:
            self.alloc = min(time / self.movestogo + inc / 2, time)
        else:
            self.alloc = float('inf')

        self.stability = 0            
        self.alloc = self.alloc / 1000
        self.ideal_alloc = self.alloc

    def time_elapsed(self):
        return perf_counter() - self.start

    def out_of_time(self) -> bool:
        '''Check if we are out of time.'''

        if self.depth and self.time_elapsed() + MOVE_OVERHEAD >= self.alloc:
            self.search_flag.value = False
            return True
        
        return False

    def update(self, values: list[Value], best_moves: list[Move]) -> None:
        '''Recalculates allocated time.'''

        self.depth += 1

        if self.depth < 5 or not self.time:
            return

        if best_moves[-1] == best_moves[-2]:
            self.stability = min(1, self.stability + 0.14)
        else:
            self.stability = 0

        difference = values[-1] - values[-2]

        if abs(difference) <= 8:
            return

        if difference < 0:
            self.alloc *= min(1.16, 1.04 * (-difference // 8))
        else:
            self.alloc *= min(1.04, 1.02 * (difference // 8))

        if (values[-1] < 1000
            and self.time_elapsed() > (2 - self.stability) * self.alloc / 2):
            self.search_flag.value = False
        
