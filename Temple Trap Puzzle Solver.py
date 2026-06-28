import heapq
import re
from collections import deque
from enum import Enum
from typing import Set, List, Tuple, Dict, Optional
import time

class Layer(Enum):
    GROUND=0
    TOP=1

class Side(Enum):
    I=1   
    II=2 
    III=3 
    IV=4

CELL_NEIGHBORS:Dict[Tuple[int,Side],int]={}
for r in range(3):
    for c in range(3):
        idx=r*3+c
        if r>0:CELL_NEIGHBORS[(idx,Side.I)]=(r-1)*3+c
        if c<2:CELL_NEIGHBORS[(idx, Side.II)]=r*3+(c+1)
        if r<2:CELL_NEIGHBORS[(idx,Side.III)]=(r+1)*3+c
        if c>0:CELL_NEIGHBORS[(idx,Side.IV)]=r*3+(c-1)

OPPOSITE_SIDE:Dict[Side,Side]={Side.I:Side.III,Side.III:Side.I,Side.II:Side.IV,Side.IV:Side.II}

TILE_DATA={'A':[{'opens_top':{Side.I,Side.II},'opens_ground':set(),'has_hole':False,'is_stair':False},{'opens_top':{Side.II,Side.III},'opens_ground':set(),'has_hole':False,'is_stair':False},{'opens_top':{Side.III, Side.IV},'opens_ground':set(),'has_hole':False,'is_stair':False},{'opens_top':{Side.IV,Side.I},'opens_ground':set(),'has_hole':False,'is_stair':False}],'B':[{'opens_top':{Side.I,Side.II},'opens_ground':set(),'has_hole':False,'is_stair':False},{'opens_top':{Side.II,Side.III},'opens_ground':set(),'has_hole':False,'is_stair':False},{'opens_top':{Side.III, Side.IV},'opens_ground':set(),'has_hole':False,'is_stair':False},{'opens_top':{Side.IV,Side.I},'opens_ground':set(),'has_hole':False,'is_stair':False}],'C':[{'opens_top':{Side.I,Side.III},'opens_ground':set(),'has_hole':False,'is_stair':False},{'opens_top':{Side.II,Side.IV},'opens_ground':set(),'has_hole':False,'is_stair':False},{'opens_top':{Side.III,Side.I},'opens_ground':set(),'has_hole':False,'is_stair':False},{'opens_top':{Side.IV,Side.II},'opens_ground':set(),'has_hole':False,'is_stair':False}],'D':[{'opens_top':{Side.IV},'opens_ground':{Side.II},'has_hole':True,'is_stair':True},{'opens_top':{Side.I},'opens_ground':{Side.III},'has_hole': True,'is_stair':True},{'opens_top':{Side.II},'opens_ground':{Side.IV},'has_hole':True,'is_stair':True},{'opens_top':{Side.III},'opens_ground':{Side.I},'has_hole':True,'is_stair':True}],'E':[{'opens_top':{Side.IV},'opens_ground':{Side.II},'has_hole':True,'is_stair':True},{'opens_top':{Side.I},'opens_ground':{Side.III},'has_hole':True,'is_stair':True},{'opens_top':{Side.II},'opens_ground':{Side.IV},'has_hole':True,'is_stair':True},{'opens_top':{Side.III},'opens_ground':{Side.I},'has_hole':True,'is_stair':True}],'F':[{'opens_top':set(),'opens_ground':{Side.I, Side.II},'has_hole':True,'is_stair':False},{'opens_top':set(),'opens_ground':{Side.II,Side.III},'has_hole':True,'is_stair':False},{'opens_top':set(),'opens_ground':{Side.III,Side.IV},'has_hole':True,'is_stair':False},{'opens_top':set(),'opens_ground':{Side.IV,Side.I},'has_hole':True,'is_stair':False}],'G':[{'opens_top':set(),'opens_ground':{Side.I,Side.II},'has_hole':True,'is_stair':False},{'opens_top':set(),'opens_ground':{Side.II,Side.III},'has_hole':True,'is_stair':False},{'opens_top':set(),'opens_ground':{Side.III,Side.IV},'has_hole':True,'is_stair':False},{'opens_top':set(),'opens_ground':{Side.IV,Side.I},'has_hole':True,'is_stair':False}],'H':[{'opens_top':set(),'opens_ground':{Side.I,Side.II},'has_hole':True,'is_stair':False},{'opens_top':set(),'opens_ground':{Side.II,Side.III},'has_hole':True,'is_stair':False},{'opens_top':set(),'opens_ground':{Side.III, Side.IV},'has_hole':True,'is_stair':False},{'opens_top':set(),'opens_ground':{Side.IV,Side.I},'has_hole':True,'is_stair':False}],' ':[{'opens_top': set(),'opens_ground':set(),'has_hole': False,'is_stair':False}]}
FAST_TILE_DATA = {}
for tile_id, rotations in TILE_DATA.items():
    for i, config in enumerate(rotations):
        FAST_TILE_DATA[(tile_id, i)] = config

EXIT_TILE_CONFIGS=set()
for tile_id, rotations in TILE_DATA.items():
    if tile_id==' ': continue
    for i,config in enumerate(rotations):
        if Side.IV in config['opens_top'] or Side.IV in config['opens_ground']:
            EXIT_TILE_CONFIGS.add((tile_id,i))

BoardLayoutType=Tuple[Tuple[str,int],...]

class State:
    __slots__ = ('board_layout', 'pawn_cell', 'pawn_layer', 'blank_idx', '_hash')
    
    def __init__(self,board_layout:BoardLayoutType,pawn_cell:int,pawn_layer:Layer, blank_idx:int=None):
        self.board_layout=board_layout
        self.pawn_cell=pawn_cell    
        self.pawn_layer=pawn_layer
        if blank_idx is None:
            for i, (tid, _) in enumerate(board_layout):
                if tid == ' ':
                    self.blank_idx = i
                    break
        else:
            self.blank_idx = blank_idx
        self._hash = hash((self.board_layout, self.pawn_cell, self.pawn_layer))
        
    def __eq__(self,other):
        return self.board_layout==other.board_layout and \
               self.pawn_cell==other.pawn_cell and \
               self.pawn_layer==other.pawn_layer
               
    def __hash__(self):
        return self._hash
        
    def __lt__(self,other):
        return self._hash < other._hash
        
    def __str__(self):
        board=[]
        for tile_id,rot in self.board_layout:
            if tile_id==' ': board.append(' _ ')
            else: board.append(f"{tile_id}[{rot}]")
        if self.pawn_cell != -1:
            pawn_char='P' if self.pawn_layer==Layer.GROUND else 'p'
            board[self.pawn_cell]=f"({board[self.pawn_cell]}{pawn_char})"
        s=""
        for i in range(3):
            s+=" ".join(board[i*3:i*3+3]).ljust(20)+"\n"
        if self.pawn_cell == -1: s += "PAWN EXITED BOARD\n"
        return s

def get_tile_properties(board_layout:BoardLayoutType,cell:int)->Dict:
    return FAST_TILE_DATA[board_layout[cell]]

def _find_all_reachable_spots_bfs(board_layout:BoardLayoutType,start_cell:int,start_layer:Layer)->Dict[Tuple[int,Layer],int]:
    q=deque([(start_cell,start_layer)])
    visited_spots={(start_cell,start_layer): 0}
    
    while q:
        current_cell,current_layer=q.popleft()
        current_dist = visited_spots[(current_cell,current_layer)]
        current_tile_data=get_tile_properties(board_layout,current_cell)
        
        if current_tile_data['is_stair']:
            other_layer=Layer.GROUND if current_layer==Layer.TOP else Layer.TOP
            if (current_cell,other_layer) not in visited_spots:
                visited_spots[(current_cell,other_layer)] = current_dist
                q.appendleft((current_cell,other_layer))
                
        for side in Side:
            if (current_cell,side) not in CELL_NEIGHBORS: continue
            neighbor_cell=CELL_NEIGHBORS[(current_cell,side)]
            if board_layout[neighbor_cell][0] == ' ': continue
            
            neighbor_tile_data=get_tile_properties(board_layout,neighbor_cell)
            opposite_neighbor_side=OPPOSITE_SIDE[side]
            openings='opens_top' if current_layer==Layer.TOP else 'opens_ground'
            
            if side in current_tile_data[openings] and opposite_neighbor_side in neighbor_tile_data[openings]:
                if (neighbor_cell,current_layer) not in visited_spots:
                    visited_spots[(neighbor_cell,current_layer)] = current_dist + 1
                    q.append((neighbor_cell,current_layer))
    return visited_spots

def get_neighbors(state: State)->List[Tuple[State,int]]:
    if state.pawn_cell == -1: return []
        
    next_states_and_costs=[]
    board_layout=state.board_layout
    blank_idx=state.blank_idx
    blank_r,blank_c=divmod(blank_idx,3)
    
    # 1. Tile Slides
    for dr, dc in [(0,1),(0,-1),(1,0),(-1,0)]:
        tile_r,tile_c=blank_r+dr,blank_c+dc
        if not (0<=tile_r<3 and 0<=tile_c<3): continue
        tile_idx=tile_r*3+tile_c
        
        if state.pawn_cell==tile_idx and get_tile_properties(board_layout,tile_idx)['has_hole']:
            continue
            
        new_board_list=list(board_layout)
        new_board_list[blank_idx],new_board_list[tile_idx]=new_board_list[tile_idx],new_board_list[blank_idx]
        new_pawn_cell = blank_idx if state.pawn_cell==tile_idx else state.pawn_cell
        new_state=State(tuple(new_board_list),new_pawn_cell,state.pawn_layer, blank_idx=tile_idx)
        next_states_and_costs.append((new_state,1))
    reachable_spots=_find_all_reachable_spots_bfs(board_layout,state.pawn_cell,state.pawn_layer)
    for (new_cell, new_layer), dist in reachable_spots.items():
        if (new_cell, new_layer)==(state.pawn_cell,state.pawn_layer): continue
        if get_tile_properties(board_layout,new_cell)['has_hole']:
            new_state=State(board_layout,new_cell,new_layer, blank_idx=blank_idx)
            next_states_and_costs.append((new_state, dist))
    if board_layout[0][0] != ' ':
        tile_data = get_tile_properties(board_layout, 0)
        
        if Side.IV in tile_data['opens_top'] and (0, Layer.TOP) in reachable_spots:
            new_state = State(board_layout, -1, Layer.TOP, blank_idx=blank_idx)
            next_states_and_costs.append((new_state, reachable_spots[(0, Layer.TOP)] + 1))
            
        elif Side.IV in tile_data['opens_ground'] and (0, Layer.GROUND) in reachable_spots:
            new_state = State(board_layout, -1, Layer.GROUND, blank_idx=blank_idx)
            next_states_and_costs.append((new_state, reachable_spots[(0, Layer.GROUND)] + 1))
            
    return next_states_and_costs

def is_goal(state: State)->bool:
    return state.pawn_cell == -1

def heuristic(state:State)->int:
    if state.pawn_cell == -1: return 0
        
    blank_r, blank_c = divmod(state.blank_idx, 3)
    min_tile_h = float('inf')
    for cell_idx, tile_config in enumerate(state.board_layout):
        if tile_config in EXIT_TILE_CONFIGS:
            row, col = divmod(cell_idx, 3)
            dist_to_0 = row + col
            
            if dist_to_0 == 0:
                tile_h = 0
            else:
                dist_to_blank = abs(row - blank_r) + abs(col - blank_c)
                tile_h = dist_to_0 + max(0, dist_to_blank - 1)
                
            if tile_h < min_tile_h:
                min_tile_h = tile_h
                
    exit_md = min_tile_h if min_tile_h != float('inf') else 0
        
    pawn_r,pawn_c = divmod(state.pawn_cell, 3)
    pawn_md = pawn_r + pawn_c
    return exit_md + pawn_md + 1

def reconstruct_path(came_from:Dict[State,State],goal_state:State)->List[State]:
    path=[]
    current=goal_state
    while current in came_from:
        path.append(current)
        current=came_from[current]
    path.append(current) 
    return path[::-1]

def solve(initial_state:State)->Optional[Tuple[List[State], int]]:
    pq:List[Tuple[int,int,State]]=[]
    initial_g_cost=0
    initial_h_cost=heuristic(initial_state)
    heapq.heappush(pq,(initial_g_cost+initial_h_cost,initial_g_cost,initial_state))
    g_costs:Dict[State,int]={initial_state:0}
    came_from:Dict[State,State]={}
    
    while pq:
        f_cost,g_cost,current_state=heapq.heappop(pq)
        if g_cost>g_costs[current_state]: continue
        
        if is_goal(current_state):
            print("\nGoal reached!")
            print(f"Total states evaluated: {len(g_costs)}")
            return reconstruct_path(came_from,current_state), g_cost
            
        for neighbor_state,action_cost in get_neighbors(current_state):
            new_g_cost=g_cost+action_cost
            if neighbor_state not in g_costs or new_g_cost<g_costs[neighbor_state]:
                g_costs[neighbor_state]=new_g_cost
                came_from[neighbor_state]=current_state
                f_cost=new_g_cost+heuristic(neighbor_state)
                heapq.heappush(pq,(f_cost,new_g_cost,neighbor_state))
    return None 

def parse_board(board_str:List[str],pawn_cell:int,pawn_layer:Layer)->State:
    board_list:List[Tuple[str,int]]=[]
    parser=re.compile(r"(\w+)\[(\d+)\]|(_)")
    for tile_match,rot_match,blank_match in parser.findall(" ".join(board_str)):
        if blank_match: board_list.append((' ', 0))
        else: board_list.append((tile_match,int(rot_match)))
    return State(tuple(board_list),pawn_cell,pawn_layer)

if __name__=="__main__":
    level_1_board=["C[1] D[0] F[2]","A[1] _ G[3]","B[0] E[0] H[2]"]
    level_1_pawn_cell=8
    initial_state=parse_board(level_1_board,level_1_pawn_cell,Layer.GROUND)
    print("Solving Level")
    start_time = time.perf_counter()
    result=solve(initial_state)
    end_time = time.perf_counter()
    if result:
        path, total_cost = result
        print(f"SOLUTION FOUND WITH TOTAL COST: {total_cost}")
        print(f"Time taken: {end_time - start_time:.4f} seconds")
        for i, state in enumerate(path):
            print(f"Move {i}:")
            print(state)
    level_2_board=["F[2] G[1] D[3]","A[2] B[1] C[0]","H[0] _ E[1]"]
    level_2_pawn_cell=6
    initial_state=parse_board(level_2_board,level_2_pawn_cell,Layer.GROUND)
    print("Solving Level 2")
    start_time = time.perf_counter()
    result=solve(initial_state)
    end_time = time.perf_counter()
    if result:
        path, total_cost = result
        print(f"SOLUTION FOUND WITH TOTAL COST: {total_cost}")
        print(f"Time taken: {end_time - start_time:.4f} seconds")
        for i, state in enumerate(path):
            print(f"Move {i}:")
            print(state)
            
    # LEVEL 3
    level_3_board=["D[1] A[2] C[0]","F[0] G[2] B[3]","H[3] E[3] _"]
    level_3_pawn_cell=0
    initial_state=parse_board(level_3_board,level_3_pawn_cell,Layer.GROUND)
    print("Solving Level 3")
    start_time = time.perf_counter()
    result=solve(initial_state)
    end_time = time.perf_counter()  
    if result:
        path, total_cost = result
        print(f"SOLUTION FOUND WITH TOTAL COST: {total_cost}")
        print(f"Time taken: {end_time - start_time:.4f} seconds")
        for i, state in enumerate(path):
            print(f"Move {i}:")
            print(state)
    level_26_board = ["B[2] A[0] D[1]", "C[1] F[2] G[1]", "_ H[3] E[3]"]
    level_26_pawn_cell = 4
    initial_state = parse_board(level_26_board, level_26_pawn_cell, Layer.GROUND)
    print("Solving EXPERT LEVEL 26")
    start_time = time.perf_counter()
    result = solve(initial_state)
    end_time = time.perf_counter()
    if result:
        path, total_cost = result
        print(f"SOLUTION FOUND WITH TOTAL COST: {total_cost}")
        print(f"Time taken: {end_time - start_time:.4f} seconds")
        for i, state in enumerate(path):
            print(f"Move {i}:")
            print(state)
    level_27_board = ["C[0] A[2] _", "B[0] H[1] D[2]", "E[0] G[0] F[2]"]
    level_27_pawn_cell = 5
    initial_state = parse_board(level_27_board, level_27_pawn_cell, Layer.TOP)
    print("Solving EXPERT LEVEL 27")
    start_time = time.perf_counter()
    result = solve(initial_state)
    end_time = time.perf_counter()
    if result:
        path, total_cost = result
        print(f"SOLUTION FOUND WITH TOTAL COST: {total_cost}")
        print(f"Time taken: {end_time - start_time:.4f} seconds")
        for i, state in enumerate(path):
            print(f"Move {i}:")
            print(state)
    level_28_board = ["B[1] E[0] F[2]", "A[0] D[0] G[2]", "H[0] C[0] _"]
    level_28_pawn_cell = 5
    initial_state = parse_board(level_28_board, level_28_pawn_cell, Layer.GROUND)
    print("Solving EXPERT LEVEL 28")
    start_time = time.perf_counter()
    result = solve(initial_state)
    end_time = time.perf_counter()
    if result:
        path, total_cost = result
        print(f"SOLUTION FOUND WITH TOTAL COST: {total_cost}")
        print(f"Time taken: {end_time - start_time:.4f} seconds")
        for i, state in enumerate(path):
            print(f"Move {i}:")
            print(state)