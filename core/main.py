import time
import threading
import queue
import numpy as np
import subprocess
import json
from enum import Enum
#from dataclasses import dataclass, field

import chess
import chess.engine 

from sshkeyboard import listen_keyboard
import RPi.GPIO as GPIO

from BoardSensorArray import BoardSensorArray
from board_event_handler import BoardEvent, board_uci_move_handler
from socket_client import Socket, wait_unix_socket


class Game:
    
    class GameState(Enum):
        WAIT_HUMAN_INPUT = 1
        WAIT_HUMAN_RETRY = 2
        WAIT_COMPUTER_INPUT = 3
        SETUP = 4
        QUIT = 5
        RESET = 6
        IDLE = 7
        
    def __init__(self):
        self.game_state = Game.GameState.IDLE
    
        #game setup
        self.game_setup:dict = {
            "computer_playing":None,"engine_strength":None,"engine_timeout":None,"side":None
        }

        #game context
        #self.is_game_running: bool = True
        self.turn:str =  "white"
        self.board = chess.Board()
        self.board_events:list = []


        self.update_display_flag:bool = False
        
        self.STOCKFISH_PATH = "/usr/games/stockfish"
        self.engine = chess.engine.SimpleEngine.popen_uci(self.STOCKFISH_PATH)
        self.engine.configure({"Skill Level": 20})

        #thread control
        self.sensor_put_queue = threading.Event()
        self.running_all_threads = threading.Event()
        self.running_all_threads.set()

        '''
        Top level class "Game" owns GPIO. Responsible for cleanup.
        '''
        self.GPIO = GPIO
        self.GPIO.setmode(GPIO.BOARD)    
        self.board_queue = queue.Queue()
        self.keyboard_queue = queue.Queue()
        self.gui_input_message_queue = queue.Queue()
        self.gui_output_message_queue = queue.Queue()
        
        self.Board_array_node = threading.Thread(target=BoardArrayWorker,args=(self.GPIO,self.running_all_threads,self.sensor_put_queue,self.board_queue),daemon=False)
        
        cb = lambda key:KeyboardWorker(key,self.keyboard_queue)
        self.Keyboard_listener_node = threading.Thread(target = listen_keyboard,args=(cb,),daemon=True)
        
        self.Gui_node = threading.Thread(target = GuiWorker ,args=('/tmp/chess_ui_socket',self.running_all_threads,self.gui_input_message_queue,self.gui_output_message_queue),daemon=False)
        
        self.Keyboard_listener_node.start()
        self.Board_array_node.start()
        self.Gui_node.start()
        

    def run(self):
        #self.board.push(chess.Move.from_uci("d2d4"))
        while True:
            self.HandleGameLogic()
            self.HandleDisplayLogic()

            time.sleep(0.03)
    
    def _switch_turn(self):
        assert self.turn == "white" or "black"
        
        if self.turn == "white":
            self.turn = "black"
        else:
            self.turn = "white"
    
    # def HandleTouchInput(self):
    #     message_json:json = self.PollQueue(self.keyboard_queue)
    #     message = json.loads(message_json)
        
    #     print(message)
    #     pass
        
    def HandleComputerInput(self):
        #TODO: interface with stockfish
        print('handling computer input:')
        result = self.engine.play(self.board, chess.engine.Limit(time=2)) 
        print("Stockfish move:", result.move)
        self.board.push(result.move)
        self.update_display_flag = True
        return self.FetchNextPlayer()

    def HandleGuiInput(self):
        msg:str = self.PollQueue(self.gui_input_message_queue)
        if msg:
            prefix, json_str = msg.split(";", 1)
            if prefix == "start":
                try:
                    self.game_setup = json.loads(json_str)
                    print("game setup:", self.game_setup)
                    print("starting game...")
                    return self.FetchNextPlayer()
                except json.JSONDecodeError as e:
                    print("Invalid JSON:", e)

            elif prefix == "reset":
                return Game.GameState.RESET

        return None
    
    def HandleIdle(self):
        return Game.GameState.IDLE
    
    @staticmethod
    def PollQueue(queue):
        if not queue.empty():
            return queue.get()
        else:
            return None
    
    def FetchNextPlayer(self):
        if self.game_setup["computer_playing"]:
            if self.turn == self.game_setup["side"]:
                next = Game.GameState.WAIT_COMPUTER_INPUT
            else:
                next = Game.GameState.WAIT_HUMAN_INPUT
        else:
            next = Game.GameState.WAIT_HUMAN_INPUT
        self._switch_turn()
        return next
    
    def HandleHumanRetry(self):
        self.sensor_put_queue.clear()
        key:str = self.PollQueue(self.keyboard_queue)
        if key == 'quit':
            
            return Game.GameState.QUIT
            #if self.game_state == GameState.WAIT_HUMAN_RETRY:
        print("await retry:")
        if key == 'completed action':
            return Game.GameState.WAIT_HUMAN_INPUT

        return Game.GameState.WAIT_HUMAN_RETRY

    def HandleHumanInput(self):
        self.sensor_put_queue.set()
        new_action = self.PollQueue(self.board_queue)
        key:str = self.PollQueue(self.keyboard_queue)
        
        # if key == 'quit':
        #     self.game_state = Game.GameState.QUIT
        #     return 
        
        if new_action:
            print(f'new move {new_action}')
            self.board_events.append(new_action)
        
        if key == 'completed action' and len(self.board_events) > 1:
            print('ff')
            success,uci_moves = board_uci_move_handler(self.board_events,self.board)
            if success:
                self.update_display_flag = True
                print(self.board)
                print('_________')
                print(uci_moves)
                next = self.FetchNextPlayer()
                
            else:
                self.update_display_flag = False
                print('retry move')
                next =  Game.GameState.WAIT_HUMAN_RETRY
                
            #reset the actions buffer
            self.board_events = []
            return next
        
        return Game.GameState.WAIT_HUMAN_INPUT
    
    def HandleGameLogic(self):
        prev_state = self.game_state 

        gui_msg = self.HandleGuiInput()
        if gui_msg:
            self.game_state = gui_msg

        if self.game_state == Game.GameState.IDLE:
            nextstate = self.HandleIdle()
        elif self.game_state == Game.GameState.WAIT_HUMAN_INPUT:
            nextstate = self.HandleHumanInput()
        elif self.game_state == Game.GameState.WAIT_COMPUTER_INPUT:
            nextstate = self.HandleComputerInput()
        elif self.game_state == Game.GameState.WAIT_HUMAN_RETRY:
            nextstate = self.HandleHumanRetry()
        elif self.game_state == Game.GameState.RESET:
            nextstate = self.HandleReset()
        elif self.game_state == Game.GameState.QUIT:
            nextstate = self.HandleQuit()
        else:
            raise ValueError(f"Invalid game state: {self.game_state}")
        
        self.game_state = nextstate 
        if prev_state != nextstate:
            print(f"next game state:{nextstate} ")

    def HandleDisplayLogic(self):
        if self.update_display_flag:
            self.update_display_flag = False
            fen:str = self.board.fen()
            '''
            sends the following string:
                "fen;"+  boardstate representation.
            for example:
                fen;rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR
            '''
            output:str = "fen;" + fen.split(' ')[0]    
            self.gui_output_message_queue.put(output)
    
    def HandleQuit(self):
        self.engine.quit()
        self.running_all_threads.clear()
        #self.gui_output_message_queue.put("quit")
        self.Gui_node.join()
        self.Board_array_node.join()
        self.GPIO.cleanup()
        exit(0)
    
    def HandleReset(self):
        self.turn:str =  "white"
        self.gui_output_message_queue.put("fen;rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR")
        self.board.reset()
        self.board_events:list = []

        return Game.GameState.IDLE
    
def GuiWorker(socket_path:str,running,input_queue,output_queue):
    
    #launch the Cpp GUI program
    server_process = subprocess.Popen(
    ["./UI/build/bin/lvglsim"],  
    stdout=subprocess.PIPE,  
    stderr=subprocess.PIPE
    )
    if not wait_unix_socket(socket_path):
        raise RuntimeError("{socket_path} not ready")
    
    with Socket(socket_path) as sock:
        while running.is_set():
            #handle inputs
            string  = sock.read_as_str()
            if string:
                input_queue.put(string)

            try:
                outbound = output_queue.get(False)
                print(f'writing outbound:{outbound}')
                sock.write(outbound)
                # if outbound == "quit":
                #     print("closing socket...")
                #     break
                
            except queue.Empty:
                continue
            
            time.sleep(0.03)
        print("closing socket...")
        sock.write('quit')
        
        
def BoardArrayWorker(GPIO,running,push_to_queue,output_queue,poll_interval=0.03):
    '''
    thread Owns BoardSensorArray which owns the SPI bus. Responsible for SPI cleanup.
    
    '''
    board_sensor_array = BoardSensorArray(GPIO=GPIO)
    prev_board_value = board_sensor_array._read_all()
    while running.is_set():
        new_board = board_sensor_array._read_all()
        if not np.array_equal(new_board, prev_board_value):
            board_event = board_array_to_uci(prev_board_value,new_board)
            if board_event is None:
                #handle board_array_to_uci errors.
                continue
            prev_board_value = new_board
            if push_to_queue.is_set():
                output_queue.put(board_event)
        time.sleep(poll_interval)    
    
    
    board_sensor_array.close_spi()
    
def board_array_to_uci(prev_array,new_array) -> BoardEvent:
    '''
    parameter: prev_array,new_array: 2d numpy array of size 8*8 
    returns: the difference of the two arrays, converted to type:event
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
    
    num:int = 8 - x
    alphabet_conversion:dict = {0:'a',1:'b',2:'c',3:'d',4:'e',5:'f',6:'g',7:'h'} 
    abcdefgh:str = alphabet_conversion[y]
    #print(f'coordinate {abcdefgh}{num}')
    
    coordinate:str = f'{abcdefgh}{num}'
    if 1 in diff:
        enable_flag = True
    else:
        enable_flag = False
    board_event = BoardEvent(enable_flag,coordinate)
    print(board_event)
    return board_event
   
#TODO: replace with 2 GPIO buttons PULLUP on each side of chessboard
def KeyboardWorker(key:str,output_queue):
    '''
    parameter: str: key from terminal
    returns: None
    Stops the main thread from sampling from Chessboard
    signaling flag for completion in main thread: None
    '''
    if key == 'z':
        print('complete action')
        output_queue.put('completed action')

    elif key == 'q':
        output_queue.put('quit')
    
    # elif key == 'x':
    #     print("starting game...")
    #     output_queue.put('start')
        
if __name__ == "__main__":
    chess_game = Game()
    chess_game.run()
    
    
        
