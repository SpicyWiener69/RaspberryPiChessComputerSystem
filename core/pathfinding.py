import chess 
import numpy as np
from typing import Optional
from collections import deque
import matplotlib.pyplot as plt
from enum import Enum, IntEnum

from board_event_handler import UciMove


class MazeT(IntEnum):
    FLOOR = 0
    WALL = 1
    START = 2
    DESTINATION = 3


class Parking():
    def __init__(self,maze:np.ndarray):
        row,_ = maze.shape
        self.row = row
        self.piece_count = 0
        #self.first_parking = True
        #self.l = deque()
        #self.l = deque([],maxlen=self.row)
        #self.r = deque([0]* self.SIDELEN * 2, maxlen=self.SIDELEN * 2)

    def mark_parking_dest(self,maze:np.ndarray) -> bool:
        #Marks parking in maze. returns False if parking is full, True if success.
        row,_ = maze.shape
        l = deque(maze[:,0].tolist(),maxlen=row)
        if self.piece_count >= self.row:
            return False
        self.piece_count += 1
        l[self.piece_count] = MazeT.DESTINATION
        # if self.first_parking:
        #     self.first_parking = False
        #     l.append(MazeT.DESTINATION)
        # else:
        #     l.append(MazeT.WALL)
        
        maze[:,0] = l

        return True

    def reset(self,maze:np.array):
        self.piece_count = 0
        self.first_parking = True
        maze[:,1] = [0 for _ in range(self.row)]

        #self.r = deque([0]* self.SIDELEN * 2, maxlen=self.SIDELEN * 2)


class Path():
    OK = 0
    NOT_FOUND = 1
    NO_PARKING_LEFT = 2

    def __init__(self,start=(),dest=(),relative_path:list[tuple[int,int]] = [],error = OK):
        self._start = start
        self._dest = dest
        self._relative_path = relative_path
        self._error = error

    def save_relative_points(self,relative_points:list[tuple]):
        self._relative_path = relative_points

    def append_relative(self,point:tuple):
        self._relative_path.append(point)
    
    def save_start_point(self,point:tuple):
        self._start = point
    
    def save_end_point(self,point:tuple):
        self.end = point
    
    def get_abs_path(self):
        r, c = self._start
        abs_path = [(r, c)]
        for dr, dc in self._relative_path:
            r += dr
            c += dc
            abs_path.append((r, c))
        return abs_path
    
class PhysicalChessboard():

    def __init__(self,board:chess.Board):
        self.board = board
        self.maze = np.zeros(shape=(15,19),dtype=np.uint8)
        self.parking = Parking(self.maze)

    def Pathfind_UCI(self,move:UciMove) -> list[Path]:
        paths = []
        start_dest_pair = self._dissect_move(move)

        #[("e8","c8"), ("a8","d8")]
        for (start_uci,dest_uci) in start_dest_pair:
            path = Path()
            
            #update the 8x8 chessboard to maze
            bitboard = self.chessboard_to_bitboard(self.board)
            print(bitboard)
            self.maze = self.update_maze_with_bitboard(self.maze,bitboard)

            #transform the uci notation into  maze coordinates
            start = self._coordinate_mapping(start_uci)
            dest = self._coordinate_mapping(dest_uci)

            #mark starting point on maze
            self._mark_endpoint(self.maze,start,MazeT.START)

            #mark destination point on maze           
            if dest == "park":
                if not self.parking.mark_parking_dest(self.maze):
                    return [Path(error=Path.NO_PARKING_LEFT)]
            else:
                self._mark_endpoint(self.maze,dest,MazeT.DESTINATION)

            #sandwich physical parking space for taken pieces
            #physical_layout = self.taken_piece_cont.sandwich_map(padded)
            
            #start pathfinding the movement
            path = self._pathfind(self.maze)
            if not path:
                return [Path(error=Path.NOT_FOUND)]
            
            self.maze = self._update_maze_after_move(self.maze)

            paths.append(path)

        return paths

    @staticmethod
    def _update_maze_after_move(maze:np.ndarray):
        '''
        update the maze markers (MazeT) after any movement. 
        '''

        start = PhysicalChessboard._find_unique_point(maze,MazeT.START)
        dest =  PhysicalChessboard._find_unique_point(maze,MazeT.DESTINATION)
        #unrecoverable error
        assert(start is not None and dest is not None)

        maze[start] = MazeT.FLOOR
        maze[dest] = MazeT.WALL  
        
        return maze

    @staticmethod
    def _mark_endpoint(maze:np.ndarray,coord:tuple,ptype:MazeT) -> np.ndarray:
        maze[coord] = ptype
        return maze
    

    @staticmethod
    def _dissect_move(move:UciMove) -> list[tuple[str,Optional[str]]]:
        assert(len(move.uci) == 4)
    
        castling_expansion = {
            "e1g1": [("e1","g1"), ("h1","f1")], 
            "e1c1": [("e1","c1"), ("a1","d1")],
            "e8g8": [("e8","g8"), ("h8","f8")], 
            "e8c8": [("e8","c8"), ("a8","d8")]
            }

        start_dest_pair = []
        if move.Movetype == move.Type.Castle:
            start_dest_pair.extend(castling_expansion[move.uci])
        elif move.Movetype == move.Type.Take:
            taken_square = move.uci[-2:]
            start_dest_pair.append((taken_square, "park"))
            start_dest_pair.append((move.uci[:2], move.uci[2:]))
        elif move.Movetype == move.Type.PureMove:     
            start_dest_pair.append((move.uci[:2], move.uci[2:]))

        elif move.Movetype == move.Type.EnPassant:
            #moves the capture pawn to the correct position
            start_dest_pair.append((move.uci[:2], move.uci[2:]))
            '''
            moves the captured pawn to "parking".
            For example, for white side capture, "e5f6". moves f5 pawn to parking. 
            For black side captures, "d4c3".  moves c4 to parking.
            '''
            start_dest_pair.append((f"{move.uci[2]}{move.uci[1]}" , "park"))
           
        else:
            raise ValueError("invalid uci type")

        return start_dest_pair
    
    @staticmethod
    def _find_unique_point(arr:np.ndarray,item) -> Optional[tuple]:
        point = tuple(np.argwhere(arr == item).flatten().tolist())
        if len(point) == 2:
            return point

        return None

    @staticmethod
    def _pathfind(maze:np.ndarray) ->  Path:
        maze = maze.copy()
        start = PhysicalChessboard._find_unique_point(maze,MazeT.START)
        end = PhysicalChessboard._find_unique_point(maze,MazeT.DESTINATION)

        if not (start and end):
            return Path(error=Path.NOT_FOUND)
        
        path = Path()
        path.save_start_point(start)
        path.save_end_point(end)

        maze[start] = 0
        row,col = maze.shape
        visited = np.zeros(shape=(row,col),dtype=bool)
        distance = np.zeros(shape=(row,col),dtype=np.int32)
        q = deque()
        q.append(start)
        visited[start] = True
        
        possible_moves = [
            (-1, 0), (1, 0), (0, -1), (0, 1) ,    # N S W E
            (-1,-1), (-1, 1), (1,-1), (1, 1)      # diagonals
        ]

        while q:
            x,y = q.popleft()
            for dx,dy in possible_moves:
                new_xy = (x + dx ,  y + dy)
                if PhysicalChessboard._validate_new_possible_position(maze,new_xy):
                    if visited[new_xy]:
                        continue
                    # if maze[new_xy] == 1:
                    #     distance[new_xy] = -1
                    q.append(new_xy)
                    visited[new_xy] = True
                    distance[new_xy]  = distance[x,y] + 1
            
        if not visited[end]:
            return None
    
        #print(maze)
        #print(visited)
        #print(distance)

        '''
        reconstruct the BFS -> path
        '''
        current_node = end
        current_distance = distance[current_node]
        relative_points = []
        while True:
            for drow,dcol in possible_moves:
                new = (current_node[0] + drow ,current_node[1] + dcol)
                if not PhysicalChessboard._validate_new_possible_position(maze,new):
                    continue
                if distance[new] == current_distance - 1:
                    current_distance -= 1
                    current_node = new  
                    relative_points.append((-drow,-dcol))
                    break
            if current_node == start:
                break
        relative_points.reverse()
        path.save_relative_points(relative_points)
       
        return path
    
    @staticmethod
    def _validate_new_possible_position(maze:np.ndarray,new_xy:tuple) -> bool:
        row,col = maze.shape
        #out of range check
        if new_xy[0] >= row or new_xy[0] < 0:
            return False   
        elif new_xy[1] >= col or new_xy[1] < 0:
            return False

        #make sure it's not an obstacle
        elif maze[new_xy] == MazeT.WALL:
            return False
        
        return True
    
    @staticmethod
    def update_maze_with_bitboard(maze:np.array,bitboard:np.ndarray) -> np.ndarray:
        #8 * 2 - 1 gets the expanded padding between each square of chessboard.
        padded_bitboard = np.zeros(shape=(8 * 2 - 1, 8 * 2 - 1),dtype=bitboard.dtype)
        padded_bitboard[::2, ::2] = bitboard

        '''overwrite the center according to the bitboard pattern:
        
        xx----15----xx 
        xx----15----xx 
        xx----15----xx 
        xx----15----xx 
        xx----15----xx
            :
            : 
            :

        '''
        maze[:,2:-2] = padded_bitboard

        return maze

    @staticmethod
    def _coordinate_mapping(coord:str) -> Optional[tuple]:
        if coord == "park":
            return "park"
        if not isinstance(coord, str):
            return None
        if len(coord) != 2:
            return None
        try:
            row = 8 - int(coord[1])
            row = row * 2 
        except ValueError:
            return None
        
        if row not in range(0,15):
            return None

        COORDINATE_MAPPING_X:dict = {
            'a' : 0, 'b': 1, 'c': 2, 'd': 3, 'e': 4, 'f': 5, 'g': 6, 'h': 7
        }
        col = COORDINATE_MAPPING_X.get(coord[0])
        if col is None:
            return None
        
        col = col* 2 + 2
        

        return (row,col)
    
    @staticmethod
    def chessboard_to_bitboard(board:chess.Board) -> np.ndarray:
        '''
        changes chessboard layout to bitboard.
        '''
        bitboard = np.zeros((8,8),dtype=np.uint8)
        for square in chess.SQUARES:
            piece = board.piece_at(square)
            if piece:  
                col = chess.square_file(square)
                row = 7 - chess.square_rank(square)
                #INTENUM
                bitboard[row,col] = 1
                #square_name = chess.square_name(square)
            
        return bitboard

    @staticmethod
    def plot_paths(
        #chessboard:chess.Board,
        maze: np.ndarray,
        paths:list[Path]
    ) -> plt.Figure:

        subplot_count = len(paths)
        fig, axes = plt.subplots(1, subplot_count, figsize=(5 * subplot_count, 5))

        if subplot_count == 1:
            axes = [axes]

        for idx, path in enumerate(paths):
            #transform the 8x8 chessboard to a padded maze, for pathfinding
            # bitboard = PhysicalChessboard.chessboard_to_bitboard(chessboard)
            # padded = PhysicalChessboard.update_maze_with_bitboard(maze,bitboard)

            (H, W) = maze.shape
            ax = axes[idx]
            
            # Build absolute coordinates from relative steps
            # r, c = path.start
            # coords = [(r, c)]
            # for dr, dc in path.relative_path:
            #     r += dr
            #     c += dc
            #     coords.append((r, c))
           

            rows, cols = zip(*path.get_abs_path())
            rows = np.array(rows)
            cols = np.array(cols)
            
            # Plot on this subplot
            ax.imshow(maze, origin="upper", interpolation="nearest")
            ax.plot(cols, rows, marker="o")  # default style, simple line + points
            
            # Align axes to cell centers and hide ticks
            ax.set_xlim(-0.5, W - 0.5)
            ax.set_ylim(H - 0.5, -0.5)
            ax.set_xticks([])
            ax.set_yticks([])
            ax.set_aspect("equal")
            ax.set_title(f"Path {idx + 1}")
                
        return fig

def _test_chessboard_to_bitboard():
    board = chess.Board(fen="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
    print(board)
    print("-----------------------")
    print(PhysicalChessboard.chessboard_to_bitboard(board))

    print("-----------------------")
    board = chess.Board(fen="rnbqkbnr/pp1ppppp/8/2p5/4P3/8/PPPP1PPP/RNBQKBNR w KQkq c6 0 2")
    print(board)
    print("-----------------------")
    print(PhysicalChessboard.chessboard_to_bitboard(board))

def _test_add_padding():
    a = np.array(
    [[1, 1, 1, 1, 1, 1, 1, 1,],
    [1, 1, 0, 1, 1, 1, 1, 1,],
    [0, 0, 0, 0, 0, 0, 0, 0,],
    [0, 0, 1, 0, 0, 0, 0, 0,],
    [0, 0, 0, 0, 1, 0, 0, 0,],
    [0, 0, 0, 0, 0, 0, 0, 0,],
    [1, 1, 1, 1, 0, 1, 1, 1,],
    [1, 1, 1, 1, 1, 1, 1, 1,]])
    print(a)
    print("-----------------------")
    a_padded = PhysicalChessboard.update_maze_with_bitboard(a)
    print(a_padded)

def _test_pathfind():
    grid = np.array([
    [0, 1, 3, 0],
    [1, 1, 1, 0],
    [0, 1, 0, 0],
    [2, 0, 0, 0],
    ], dtype=np.uint8)
    path = PhysicalChessboard._pathfind(grid)
    print(path.get_abs_path())

    # destination blocked
    grid = np.array([
    [1, 1, 0],
    [0, 1, 0],
    [2, 1, 1],   
    ], dtype=np.uint8)

    path = PhysicalChessboard._pathfind(grid)
    print(path._error)

    grid = np.array(
    [[1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [1, 0, 1, 0, 0, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 3, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [1, 0, 1, 0, 1, 0, 1, 0, 2, 0, 1, 0, 1, 0, 1],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1]]
    )
    path = PhysicalChessboard._pathfind(grid)
    print(path.get_abs_path())

    #PhysicalChessboard._plot_paths(grid,(14,12),path)
    #plt.show()

def _test_coordinate_mapping():
    #print(PhysicalChessboard._coordinate_mapping("a1"))
    #print(PhysicalChessboard._coordinate_mapping("h8"))
    assert(PhysicalChessboard._coordinate_mapping("a8") == (0,2))
    assert(PhysicalChessboard._coordinate_mapping("a1") == (14,2))
    assert(PhysicalChessboard._coordinate_mapping("h8") == (0,16))
    assert(PhysicalChessboard._coordinate_mapping("park") == "park")
    assert(PhysicalChessboard._coordinate_mapping("h9") is None)
    assert(PhysicalChessboard._coordinate_mapping("k6") is None)
    assert(PhysicalChessboard._coordinate_mapping("asdf") is None)
    print("test successful")

def _test_plot_paths():
    board = chess.Board(fen="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
    path1 = Path(start=(12,10),dest=(8,10),relative_path=[(-1,0),(-1,0),(-1,0),(-1,0)])
    path2 = Path(start=(12,8),dest=(8,8),relative_path=[(-1,0),(-1,0),(-1,0),(-1,0)])
    maze = np.zeros((15,19),dtype=np.uint8)
    fig = PhysicalChessboard.plot_paths(maze,[path1,path2])
    
    #maze = np.zeros((15,19),dtype=np.uint8)
    # fig = PhysicalChessboard._plot_paths(board,maze,[path])
    
    
    plt.show()



def _test_integration():
    print("_______case 1: move _________")
    board = chess.Board(fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
    print(board)
    physical_chessboard = PhysicalChessboard(board=board)
    move = UciMove("e2e4", UciMove.Type.PureMove)
    paths = physical_chessboard.Pathfind_UCI(move)
    physical_chessboard.plot_paths(maze=physical_chessboard.maze,paths=paths)
    plt.show()

    print("_______case 2:take_________")
    board = chess.Board(fen = "rnbqkbnr/ppp1pppp/8/3p4/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 1")
    print(board)
    physical_chessboard = PhysicalChessboard(board=board)
    move = UciMove("e4d5", UciMove.Type.Take)
    paths = physical_chessboard.Pathfind_UCI(move)
    physical_chessboard.plot_paths(maze=physical_chessboard.maze,paths=paths)
    plt.show()

    print("_______case 3: castling_________")
    board = chess.Board(fen = "rnb1kbnr/ppp3pp/3q4/1B1ppp2/4P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 0 1")
    print(board)
    physical_chessboard = PhysicalChessboard(board=board)
    move = UciMove("e1g1", UciMove.Type.Castle)
    paths = physical_chessboard.Pathfind_UCI(move)
    physical_chessboard.plot_paths(paths=paths,maze=physical_chessboard.maze)
    plt.show()

    print("_______case 4: en passant:1_________")
    board = chess.Board(fen = "rnbqkbnr/ppp1p1pp/8/4Pp2/2Pp1P2/8/PP1P2PP/RNBQKBNR b KQkq - 0 1")
    print(board)
    physical_chessboard = PhysicalChessboard(board=board)
    move = UciMove("e5f6", UciMove.Type.EnPassant)
    paths = physical_chessboard.Pathfind_UCI(move)
    physical_chessboard.plot_paths(paths=paths,maze=physical_chessboard.maze)
    plt.show()

    print("_______case 4: en passant:2________")
    board = chess.Board(fen = "rnbqkbnr/ppp1p1pp/8/4Pp2/2Pp1P2/8/PP1P2PP/RNBQKBNR b KQkq - 0 1")
    print(board)
    physical_chessboard = PhysicalChessboard(board=board)
    move = UciMove("c4d3", UciMove.Type.EnPassant)
    paths = physical_chessboard.Pathfind_UCI(move)
    physical_chessboard.plot_paths(paths=paths,maze=physical_chessboard.maze)
    plt.show()

    print("_______case 5: take twice________")
    board = chess.Board(fen = "rnbqkbnr/pp2pppp/8/2pp4/3PP3/8/PPP2PPP/RNBQKBNR w KQkq - 0 1")
    physical_chessboard = PhysicalChessboard(board=board)
    print("-------------")
    move = UciMove("e4d5", UciMove.Type.Take)
    paths = physical_chessboard.Pathfind_UCI(move)
    physical_chessboard.plot_paths(paths=paths,maze=physical_chessboard.maze)
    print(board)
    print("-------------")
    board.push_uci(move.uci)
    print(board)
    print("-------------")
    plt.show()


    move = UciMove("c5d4", UciMove.Type.Take)
    print(board)
    print("-------------")
    paths = physical_chessboard.Pathfind_UCI(move)
    physical_chessboard.plot_paths(paths=paths,maze=physical_chessboard.maze)
    board.push_uci(move.uci)
    print(board)
    print("-------------")
    plt.show()



if __name__ == "__main__":  
    #_test_coordinate_mapping()
    #_test_chessboard_to_bitboard()
    #_test_add_padding()
    #_test_pathfind()
    #_test_plot_paths()
    _test_integration()
