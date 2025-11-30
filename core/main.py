import time
import threading
import queue
import numpy as np
import chess

from sshkeyboard import listen_keyboard
import RPi.GPIO as GPIO

from BoardSensorArray import BoardSensorArray
from board_event_handler import event, board_uci_move_handler

def BoardArrayWorker(sensor,poll_interval=0.03):
    while True:
        prev_board_value = board_sensor_array._read_all()
        while running.is_set():
            new_board = board_sensor_array._read_all()
            if not np.array_equal(new_board, prev_board_value):
                print(f'res {new_board}  prev {prev_board_value}')
                board_event = board_array_to_uci(prev_board_value,new_board)
                prev_board_value = new_board
                board_queue.put(board_event)
                new_board_state.set()
                time.sleep(0.5)
            time.sleep(poll_interval)
        
    
def board_array_to_uci(prev_array,new_array) ->event:
    '''
    parameter: prev_array,new_array: 2d numpy array of size 8*8 
    returns: the difference of the two arrays, converted to type:event
    '''
    #assert prev_array.shape == (8,8)
    #assert new_array.shape == (8,8)
    diff = np.subtract(new_array,prev_array)
    print(f'diff:{diff}')
    assert np.count_nonzero(diff) == 1
    x,y = np.where(diff != 0)
    x,y = int(x[0]),int(y[0])
    
    num = 8 - x
    alphabet_conversion = {0:'a',1:'b',2:'c',3:'d',4:'e',5:'f',6:'g',7:'h'} 
    abcdefgh = alphabet_conversion[y]
    #print(f'coordinate {abcdefgh}{num}')
    
    coordinate = f'{abcdefgh}{num}'
    if 1 in diff:
        enable_flag = True
    else:
        enable_flag = False
    board_event = event(enable_flag,coordinate)
    print(board_event)
    return board_event
   
def on_press(key):
    '''
    parameter: str: key from terminal
    returns: None
    Stops the main thread from sampling from Chessboard
    signaling flag for main thread: type None
    '''
    if key == 'z':
        running.clear()
        board_queue.put(None)
        
        
        
if __name__ == "__main__":
    chessboard = chess.Board()
    print(chessboard)
    ##testing black pieces for now. premove white
    chessboard.push(chess.Move.from_uci("d2d4"))
    print(chessboard)
    
    board_queue = queue.Queue()
    new_board_state = threading.Event()
    running = threading.Event()
    
    GPIO.setmode(GPIO.BOARD)    
    board_sensor_array = BoardSensorArray(GPIO=GPIO)
    Board_array_node = threading.Thread(target=BoardArrayWorker,args=(board_sensor_array,),daemon=True)
    Keyboard_listener_node = threading.Thread(target = listen_keyboard,args=(on_press,),daemon=True)
    
    Keyboard_listener_node.start()
    Board_array_node.start()
    
    attempt_count = 0
    while attempt_count < 3:
        
        running.set()
        event_buffer = []
        while (True):
            new_move = board_queue.get()
            if new_move is None:
                break
            event_buffer.append(new_move)
                
        success,uci_moves = board_uci_move_handler(event_buffer,chessboard)
        
        if success:
            print(chessboard)
            break
        else:
            print('retry move')
    
    
