import chess
import itertools
from icecream import ic

class event:
    def __init__(self, enabled:bool, coordinate: str):
        self.coordinate = coordinate        
        self.enabled = enabled

    def __str__(self):
        string = f"{self.coordinate} down" if self.enabled else f"{self.coordinate} up"
        return string

    
def board_uci_move_handler(events_list,board) -> tuple:
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

    move = chess.Move.from_uci(uci_moves)
    if move in board.legal_moves:
        board.push(move)
        return (1, uci_moves)
    ic(f"Illegal move: {uci_moves}")
    return (0,uci_moves)


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
    event_list.append(event(False,"e2"))
    event_list.append(event(True,"e4"))  
    board_uci_move_handler(event_list,board)
    print(board)
    print("--------------------------------")
   
    event_list = []
    event_list.append(event(False,"d7"))
    event_list.append(event(True,"d5"))  
    board_uci_move_handler(event_list,board)
    print(board)
    print("--------------------------------")

    event_list = []
    event_list.append(event(False,"e4"))
    event_list.append(event(False,"d5"))  
    event_list.append(event(True,"d5"))  
    board_uci_move_handler(event_list,board)
    print(board)
    print("--------------------------------")

def _test_castling():
    
    #Test castling
    board = chess.Board("rnbqkbnr/p1p4p/3p4/4p1p1/1pBPPp2/2N1BN2/PPP1QPPP/R3K2R w KQkq - 0 8")
    print(board)
    print("--------------------------------")
    event_list = []
    event_list.append(event(False,"e1"))
    event_list.append(event(False,"a1"))  
    event_list.append(event(True,"c1"))  
    event_list.append(event(True,"d1"))  
    board_uci_move_handler(event_list,board)
    print(board)
    print("--------------------------------")

    board = chess.Board("rnbqkbnr/p1p4p/3p4/4p1p1/1pBPPp2/2N1BN2/PPP1QPPP/R3K2R w KQkq - 0 8")
    print(board)
    print("--------------------------------")
    event_list = []
    event_list.append(event(False,"h1"))
    event_list.append(event(False,"e1"))  
    event_list.append(event(True,"g1"))  
    event_list.append(event(True,"f1"))  
    board_uci_move_handler(event_list,board)
    print(board)
    print("--------------------------------")

    board = chess.Board("rnbqk2r/p1p1b2p/3p3n/4p1p1/1p1PPp1N/2NBB3/PPP1QPPP/R4RK1 b kq - 5 10")
    print(board)
    print("--------------------------------")
    event_list = []
    event_list.append(event(False,"e8"))
    event_list.append(event(False,"h8"))  
    event_list.append(event(True,"g8"))  
    event_list.append(event(True,"f8"))  
    board_uci_move_handler(event_list,board)
    print(board)
    print("--------------------------------")

def _test_promotion():
    board = chess.Board("rn3bnr/pb1Pkp1p/5q2/1pp1p1p1/1P4P1/3B4/P1PP1P1P/RNBQ1KNR w - - 1 9")
    print(board)
    print("--------------------------------")
    event_list = []
    event_list.append(event(False,"d7"))
    event_list.append(event(True,"d8"))  
    board_uci_move_handler(event_list,board)
    print(board)
    print("--------------------------------")

    board = chess.Board("2r2bnr/pb1Pkp1p/n4q2/1pp1p1p1/1P4P1/1B6/P1PP1P1P/RNBQ1KNR w - - 5 11")
    print(board)
    print("--------------------------------")
    event_list = []
    event_list.append(event(False,"d7"))
    event_list.append(event(False,"c8")) 
    event_list.append(event(True,"c8"))   
    board_uci_move_handler(event_list,board)
    print(board)
    print("--------------------------------")

if __name__ == "__main__":
    #_test_moves()
    #_test_castling()
    _test_promotion()    



