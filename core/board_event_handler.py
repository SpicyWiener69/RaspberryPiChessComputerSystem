import chess
import numpy as np
from typing import Optional
from enum import Enum


class UciMove():
    class Type(Enum):
        Castle = 1
        Take = 2
        PureMove = 3
        EnPassant = 4
        
    def __init__(self,uci:str,movetype:Type):
        #assert(len(uci4) == 4)
        self.uci = uci
        if len(self.uci) == 5:
            self.promotion_piece:str = self.uci[-1]
        
        self.Movetype = movetype
        #return self

    def get_uci4(self):
        # Always returns the 4-character move (origin+destination) 
        # regardless of promotion. Used by pathfinding algorithm.
        return self.uci[:4]
       
    def get_uci(self):
        # Returns proper UCI string. used for python-chess interfacing.
        return self.uci
    
class BoardEvent:
    def __init__(self, enabled:bool, coordinate: str):
        self.coordinate = coordinate        
        self.enabled = enabled

    def __str__(self):
        string = f"{self.coordinate} down" if self.enabled else f"{self.coordinate} up"
        return string
    
    
def board_uci_move_handler(events_list,board:chess.Board) -> Optional[UciMove]:
    '''
    if the event list is valid: returns the converted UciMove instance.
    else: returns None
    '''
    
    uci_str = ""
    move_type = None
    

    # Castling check
    if len(events_list) == 4:
        uci_str = check_castling(events_list,board)
        move_type = UciMove.Type.Castle
         
    else:
        uci_str = handle_move(events_list)
        #Promotion check
        promotion = check_promotion(events_list,board)
        uci_str += promotion

    try:
        move = chess.Move.from_uci(uci_str)
    except chess.InvalidMoveError:
        print(f"Illegal move: {uci_str}")
        return None

    if board.is_en_passant(move):
        move_type = UciMove.Type.EnPassant
    elif board.is_capture(move):
        move_type = UciMove.Type.Take
    else:
        move_type = UciMove.Type.PureMove
    
    
    return UciMove(uci_str,move_type)


def diff_board_array_to_event(prev_array:np.array,new_array:np.array) -> BoardEvent:
    '''
    Compute the difference between two 8x8 board arrays and return as a BoardEvent.
    
    parameters: 
        prev_array,new_array: 2d numpy array of size 8*8 
    
    returns: 
        the difference of the two arrays, converted to type:event
    '''
    #assert prev_array.shape == (8,8)
    #assert new_array.shape == (8,8)
    diff = np.subtract(new_array,prev_array)
    
    #count the difference of between two scannings.
    #if count is not 1(magnets may be between board sensors) ignore.
    if np.count_nonzero(diff) != 1:
        return None
    
    x,y = np.where(diff != 0)
    x,y = int(x[0]),int(y[0])
    
    num:int = x + 1
    alphabet_conversion:dict = {0:'a',1:'b',2:'c',3:'d',4:'e',5:'f',6:'g',7:'h'} 
    abcdefgh:str = alphabet_conversion[y]
    #print(f'coordinate {abcdefgh}{num}')
    
    coordinate:str = f'{abcdefgh}{num}'
    if 1 in diff:
        enable_flag = True
    else:
        enable_flag = False
    board_event = BoardEvent(enable_flag,coordinate)
    return board_event


def handle_move(events_list) -> str:

    #pure move
    if len(events_list) == 2:
        origin = events_list[0].coordinate
        destination = events_list[1].coordinate

    # capture move
    elif len(events_list) == 3:
        destination = events_list[-1].coordinate
        # The origin is whichever of the first two events is NOT the destination
        if events_list[0].coordinate != destination:
            origin = events_list[0].coordinate
        else:
            origin = events_list[1].coordinate
    else:
        # Invalid event list length
        return None
    return origin + destination


def check_castling(events_list,board) -> Optional[str]:
    possible_castling_moves ={
    (
    ('e1', 'h1', 'f1', 'g1'),
    ('e1', 'h1', 'g1', 'f1'),
    ('h1', 'e1', 'f1', 'g1'),
    ('h1', 'e1', 'g1', 'f1')):"e1g1",

    (
    ('e1', 'a1', 'c1', 'd1'),
    ('e1', 'a1', 'd1', 'c1'),
    ('a1', 'e1', 'c1', 'd1'),
    ('a1', 'e1', 'd1', 'c1')):"e1c1",

    (
    ('e8', 'h8', 'f8', 'g8'),
    ('e8', 'h8', 'g8', 'f8'),
    ('h8', 'e8', 'f8', 'g8'),
    ('h8', 'e8', 'g8', 'f8')):"e8g8",

    (
    ('e8', 'a8', 'c8', 'd8'),
    ('e8', 'a8', 'd8', 'c8'),
    ('a8', 'e8', 'c8', 'd8'),
    ('a8', 'e8', 'd8', 'c8')):"e8c8"
    }

    events_list_enabled = tuple([e.enabled for e in events_list])
    if events_list_enabled != (False,False,True,True):
        return None
    
    events_list_coords = tuple([e.coordinate for e in events_list])
    for key,uci in possible_castling_moves.items():
        if events_list_coords in key:
            return uci
    return None


def check_promotion(events_list,board) -> str:
    start_square = events_list[0].coordinate
    piece = board.piece_at(chess.parse_square(start_square))
    if piece is None or piece.piece_type != chess.PAWN:
        return ""
    destination_square = events_list[-1].coordinate
    rank = destination_square[-1] 
    if (piece.color == chess.WHITE and rank == '8') or (piece.color == chess.BLACK and rank == '1'):
        return ask_for_promotion_piece()

    return ""

def ask_for_promotion_piece() -> str:
    #For now always queen
    return 'q'


def piece_on_ourside(board,coordinate)->bool:
    square_index = chess.parse_square(coordinate)
    piece = board.piece_at(square_index)
    if piece is None:
        return False
    if piece.color == board.turn:
        return True
    return False

def _test_moves():
    board = chess.Board()
    event_list = []
    event_list.append(BoardEvent(False,"e2"))
    event_list.append(BoardEvent(True,"e4"))  
    uci_move = board_uci_move_handler(event_list,board)
    board.push_uci(uci_move.uci)
    print(board)
    print("--------------------------------")
   
    event_list = []
    event_list.append(BoardEvent(False,"d7"))
    event_list.append(BoardEvent(True,"d5"))  
    uci_move = board_uci_move_handler(event_list,board)
    board.push_uci(uci_move.uci)
    print(board)

    print("-------------take:case 1---------------")
    event_list = []
    event_list.append(BoardEvent(False,"e4"))
    event_list.append(BoardEvent(False,"d5"))  
    event_list.append(BoardEvent(True,"d5"))  
    uci_move = board_uci_move_handler(event_list,board)
    board.push_uci(uci_move.uci)
    print(board)

    print("-------------take:case 2---------------")
    board = chess.Board(fen = "rnbqkbnr/ppp1pppp/8/3p4/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2")
    print(board)
    print("--------------------------------")
    event_list = []
    event_list.append(BoardEvent(False,"d5"))  
    event_list.append(BoardEvent(False,"e4"))
    event_list.append(BoardEvent(True,"d5")) 
    uci_move = board_uci_move_handler(event_list,board)
    board.push_uci(uci_move.uci)
    print(board)

def _test_castling():
    
    #Test castling
    board = chess.Board("rnbqkbnr/p1p4p/3p4/4p1p1/1pBPPp2/2N1BN2/PPP1QPPP/R3K2R w KQkq - 0 8")
    print(board)
    print("--------------------------------")
    event_list = []
    event_list.append(BoardEvent(False,"e1"))
    event_list.append(BoardEvent(False,"a1"))  
    event_list.append(BoardEvent(True,"c1"))  
    event_list.append(BoardEvent(True,"d1"))  
    uci_move = board_uci_move_handler(event_list,board)
    board.push_uci(uci_move.uci)
    print(board)
    print("--------------------------------")

    board = chess.Board("rnbqkbnr/p1p4p/3p4/4p1p1/1pBPPp2/2N1BN2/PPP1QPPP/R3K2R w KQkq - 0 8")
    print(board)
    print("--------------------------------")
    event_list = []
    event_list.append(BoardEvent(False,"h1"))
    event_list.append(BoardEvent(False,"e1"))  
    event_list.append(BoardEvent(True,"g1"))  
    event_list.append(BoardEvent(True,"f1"))  
    uci_move = board_uci_move_handler(event_list,board)
    board.push_uci(uci_move.uci)
    print(board)
    print("--------------------------------")

    board = chess.Board("rnbqk2r/p1p1b2p/3p3n/4p1p1/1p1PPp1N/2NBB3/PPP1QPPP/R4RK1 b kq - 5 10")
    print(board)
    print("--------------------------------")
    event_list = []
    event_list.append(BoardEvent(False,"e8"))
    event_list.append(BoardEvent(False,"h8"))  
    event_list.append(BoardEvent(True,"g8"))  
    event_list.append(BoardEvent(True,"f8"))  
    uci_move = board_uci_move_handler(event_list,board)
    board.push_uci(uci_move.uci)
    print(board)
    print("--------------------------------")

def _test_promotion():
    board = chess.Board("rn3bnr/pb1Pkp1p/5q2/1pp1p1p1/1P4P1/3B4/P1PP1P1P/RNBQ1KNR w - - 1 9")
    print(board)
    print("--------------------------------")
    event_list = []
    event_list.append(BoardEvent(False,"d7"))
    event_list.append(BoardEvent(True,"d8"))  
    uci_move = board_uci_move_handler(event_list,board)
    board.push_uci(uci_move.uci)
    print(board)
    print("--------------------------------")

    board = chess.Board("2r2bnr/pb1Pkp1p/n4q2/1pp1p1p1/1P4P1/1B6/P1PP1P1P/RNBQ1KNR w - - 5 11")
    print(board)
    print("--------------------------------")
    event_list = []
    event_list.append(BoardEvent(False,"d7"))
    event_list.append(BoardEvent(False,"c8")) 
    event_list.append(BoardEvent(True,"c8"))   
    uci_move = board_uci_move_handler(event_list,board)
    board.push_uci(uci_move.uci)
    print(board)
    print("--------------------------------")

if __name__ == "__main__":
    _test_moves()
    #_test_castling()
    #_test_promotion()    



