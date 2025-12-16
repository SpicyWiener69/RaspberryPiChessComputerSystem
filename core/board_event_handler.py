import chess
from icecream import ic
import numpy as np

class BoardEvent:
    def __init__(self, enabled:bool, coordinate: str):
        self.coordinate = coordinate        
        self.enabled = enabled

    def __str__(self):
        string = f"{self.coordinate} down" if self.enabled else f"{self.coordinate} up"
        return string

    
def board_uci_move_handler(events_list,board:chess.Board) -> tuple:
    '''
    modifies the given chess.Board if the event list is valid.
    else, leaves chess.Board untouched and returns 0, with the converted uci_moves.
    '''
    print(events_list)
    uci_moves = ""
    castling = check_castling(events_list,board)
    if castling:
        uci_moves = castling

    else:
        uci_moves = handle_move(events_list)
        #Promotion check
        promotion = check_promotion(events_list,board)
        if promotion:
            uci_moves += promotion
    try:
        move = chess.Move.from_uci(uci_moves)
    except chess.InvalidMoveError:
        ic(f"Illegal move: {uci_moves}")
        return (0,uci_moves)
    
    if move in board.legal_moves:
        board.push(move)
        return (1, uci_moves)
    ic(f"Illegal move: {uci_moves}")
    return (0,uci_moves)


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
    move = events_list[0].coordinate + events_list[1].coordinate
    return move

def check_castling(events_list,board) -> str:
    if len(events_list) != 4:
        return None

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
        return None
    destination_square = events_list[-1].coordinate
    rank = destination_square[-1] 
    if (piece.color == chess.WHITE and rank == '8') or (piece.color == chess.BLACK and rank == '1'):
        return ask_for_promotion_piece()

    return None

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
    #Test pure move
    board = chess.Board()
    event_list = []
    event_list.append(BoardEvent(False,"e2"))
    event_list.append(BoardEvent(True,"e4"))  
    board_uci_move_handler(event_list,board)
    print(board)
    print("--------------------------------")
   
    event_list = []
    event_list.append(BoardEvent(False,"d7"))
    event_list.append(BoardEvent(True,"d5"))  
    board_uci_move_handler(event_list,board)
    print(board)
    print("--------------------------------")

    event_list = []
    event_list.append(BoardEvent(False,"e4"))
    event_list.append(BoardEvent(False,"d5"))  
    event_list.append(BoardEvent(True,"d5"))  
    board_uci_move_handler(event_list,board)
    print(board)
    print("--------------------------------")

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
    board_uci_move_handler(event_list,board)
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
    board_uci_move_handler(event_list,board)
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
    board_uci_move_handler(event_list,board)
    print(board)
    print("--------------------------------")

def _test_promotion():
    board = chess.Board("rn3bnr/pb1Pkp1p/5q2/1pp1p1p1/1P4P1/3B4/P1PP1P1P/RNBQ1KNR w - - 1 9")
    print(board)
    print("--------------------------------")
    event_list = []
    event_list.append(BoardEvent(False,"d7"))
    event_list.append(BoardEvent(True,"d8"))  
    board_uci_move_handler(event_list,board)
    print(board)
    print("--------------------------------")

    board = chess.Board("2r2bnr/pb1Pkp1p/n4q2/1pp1p1p1/1P4P1/1B6/P1PP1P1P/RNBQ1KNR w - - 5 11")
    print(board)
    print("--------------------------------")
    event_list = []
    event_list.append(BoardEvent(False,"d7"))
    event_list.append(BoardEvent(False,"c8")) 
    event_list.append(BoardEvent(True,"c8"))   
    board_uci_move_handler(event_list,board)
    print(board)
    print("--------------------------------")

if __name__ == "__main__":
    #_test_moves()
    #_test_castling()
    _test_promotion()    



