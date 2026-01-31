import time
import threading
from threading import Event
from queue import Queue, Empty
import subprocess
import json
import stat
import os
from enum import Enum
from dataclasses import dataclass
import argparse

import numpy as np
import chess
import chess.engine 
from sshkeyboard import listen_keyboard
import RPi.GPIO as GPIO

from board_sensor_array import BoardSensorArray
from board_event_handler import board_uci_move_handler, diff_board_array_to_event
from socket_client import Socket, wait_unix_socket
from gpio_definition import BoardPin

class Game:
    
    class GameState(Enum):
        WAIT_HUMAN_INPUT = 1
        WAIT_RETRY_MOVE_CONFIRM = 2
        WAIT_COMPUTER_INPUT = 3
        SETUP = 4
        QUIT = 5
        RESET = 6
        IDLE = 7
        WAIT_MANUAL_FOR_COMPUTER = 8
    
    @dataclass
    class GameSetup():
        computer_playing:bool
        engine_strength:int
        engine_think_time:int
        engine_side:str
        auto_mover:bool = False

        @classmethod
        def from_json(cls, json_string:str):
            """Create GameSetup instance from JSON string"""    
            try:
                data = json.loads(json_string)
                return cls(**data) 
            except TypeError as e:
                print(f"invalid json, {e}")
                raise

        def __str__(self):
            return f"""
                Game Setup:
                Computer Playing: {self.computer_playing}
                Engine Strength: {self.engine_strength}
                Engine Think Time: {self.engine_think_time}s
                Engine Side: {self.engine_side.capitalize()}
                Auto Mover: {self.auto_mover}
                """

    def __init__(self, logging:bool = False):
        self.logging = logging
        
        self.game_state = Game.GameState.IDLE
        self.game_setup = None
        #game context
        self.turn:str =  "white"
        self.board = chess.Board()
        self.board_events:list = []
        self.update_display_flag:bool = False
        
        self.STOCKFISH_PATH = "/usr/games/stockfish"
        self.engine = chess.engine.SimpleEngine.popen_uci(self.STOCKFISH_PATH)
        
        #thread control
        self.sensor_put_queue = threading.Event()
        self.sensor_put_queue.clear()   
        self.running_all_threads = threading.Event()
        self.running_all_threads.set()

        '''
        Top level class "Game" owns GPIO. Responsible for cleanup.
        '''
        self.GPIO = GPIO
        self.GPIO.setmode(GPIO.BOARD)    
        self.board_queue = Queue()
        self.keyboard_queue = Queue()
        self.gui_input_message_queue = Queue()
        self.gui_output_message_queue = Queue()
        
        self.Board_array_node = threading.Thread(target=BoardArrayWorker,args=(self.GPIO,self.running_all_threads,self.sensor_put_queue,self.board_queue),daemon=False)
        
        #closure around listen_keyboard, to pass a queue inside
        cb = lambda key:KeyboardWorker(key,self.keyboard_queue)
        self.Keyboard_listener_node = threading.Thread(target = listen_keyboard,args=(cb,),daemon=True)
        
        self.Gui_node = threading.Thread(target = GuiWorker ,args=('/tmp/chess_ui_socket',self.running_all_threads,self.gui_input_message_queue,self.gui_output_message_queue),daemon=False)
        
        self.Keyboard_listener_node.start()
        self.Board_array_node.start()
        self.Gui_node.start()
        

    def run(self):
        while True:
            self.HandleGameLogic()
            self.HandleDisplayLogic()
            time.sleep(0.03)
    
    def _ResetGameContext(self):
        self.turn:str =  "white"
        self.board.reset()
        self.board_events:list = []
        self.update_display_flag:bool = False
        self.sensor_put_queue.clear()   


    def _SwitchTurn(self):
        assert self.turn == "white" or "black"
        if self.turn == "white":
            self.turn = "black"
        else:
            self.turn = "white"


    def HandleComputerInput(self):
        result = self.engine.play(self.board, chess.engine.Limit(time=self.game_setup.engine_think_time)) 
        print("Stockfish move:", result.move)
        self.board.push(result.move)
        self.update_display_flag = True
        if self.game_setup.auto_mover is False:
            return Game.GameState.WAIT_MANUAL_FOR_COMPUTER

        return self.FetchNextPlayer()


    def HandleGuiInput(self):
        msg:str = self.PollQueue(self.gui_input_message_queue)
        if msg:
            prefix, json_str = msg.split(";", 1)
            if prefix == "start":
                self.game_setup = Game.GameSetup.from_json(json_string=json_str)
                #    &dependency injec
                self.game_setup.auto_mover = False
                print(self.game_setup)
                self.engine.configure({"UCI_LimitStrength": True, "UCI_Elo":self.game_setup.engine_strength})
                print("starting game...")

                return self.FetchNextPlayer()
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
        '''
        Depending on gamemode, return the correct next "player". checks if the outcome is decided.
        '''
        outcome = self.board.outcome()
        if outcome:
            print(outcome)
            return Game.GameState.IDLE

        if self.game_setup.computer_playing:
            if self.turn == self.game_setup.engine_side:
                next = Game.GameState.WAIT_COMPUTER_INPUT
            else:
                next = Game.GameState.WAIT_HUMAN_INPUT
        else:
            next = Game.GameState.WAIT_HUMAN_INPUT
        self._SwitchTurn()
        return next
    
    def WaitManualMoveForComputer(self):
        '''
        In absence of the automover xy system, this function will be called to for human 
        to move for the computer.
        '''
        #assert self.game_setup["auto_moving"] is False
        key:str = self.PollQueue(self.keyboard_queue)
        if key == 'completed action':
            return self.FetchNextPlayer()
        return Game.GameState.WAIT_MANUAL_FOR_COMPUTER


    def HandleRetryConfirm(self):
        #self.sensor_put_queue.clear()
        key:str = self.PollQueue(self.keyboard_queue)
        if key == 'quit':
            return Game.GameState.QUIT
        if key == 'completed action':
            return Game.GameState.WAIT_HUMAN_INPUT

        return Game.GameState.WAIT_RETRY_MOVE_CONFIRM


    def HandleHumanInput(self):
        self.sensor_put_queue.set()
        new_action = self.PollQueue(self.board_queue)
        key:str = self.PollQueue(self.keyboard_queue) 
        if new_action:
            print(f'new move {new_action}')
            self.board_events.append(new_action)

        if key == 'completed action' and len(self.board_events) > 1:
            self.sensor_put_queue.clear()
            print('parsing move:')
            move,uci_move = board_uci_move_handler(self.board_events,self.board)
            
            if move:
                self.board.push(move)
                self.update_display_flag = True
                print(self.board)
                print('_________')
                print(uci_move)
                next = self.FetchNextPlayer()
            else:
                self.update_display_flag = False
                print('retry move')
                next =  Game.GameState.WAIT_RETRY_MOVE_CONFIRM
                
            #reset the board detection buffer
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
        elif self.game_state == Game.GameState.WAIT_RETRY_MOVE_CONFIRM:
            nextstate = self.HandleRetryConfirm()
        elif self.game_state == Game.GameState.RESET:
            nextstate = self.HandleReset()
        elif self.game_state == Game.GameState.QUIT:
            nextstate = self.HandleQuit()
        elif self.game_state == Game.GameState.WAIT_MANUAL_FOR_COMPUTER:
            nextstate = self.WaitManualMoveForComputer()
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
            example:
                "fen;rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR"
            '''
            output:str = "fen;" + fen.split(' ')[0]    
            self.gui_output_message_queue.put(output)
    

    def HandleQuit(self):
        self.engine.quit()
        self.running_all_threads.clear()
        self.Gui_node.join()
        self.Board_array_node.join()
        self.GPIO.cleanup()
        exit(0)
    
    
    def HandleReset(self):
        self._ResetGameContext()
        self.gui_output_message_queue.put("fen;rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR")
        return Game.GameState.IDLE
    

def GuiWorker(socket_path:str,running,input_queue,output_queue):
    if os.path.exists(socket_path):
        mode = os.stat(socket_path).st_mode
        if stat.S_ISSOCK(mode):
            os.remove(socket_path)

    server_process = subprocess.Popen(
    ["./UI/build/bin/lvglsim"],  
    stdout=subprocess.PIPE,  
    stderr=subprocess.PIPE
    )
    if not wait_unix_socket(socket_path):
        raise RuntimeError(f"{socket_path} not ready")
    
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
            except Empty:
                continue
            
            time.sleep(0.03)
        print("closing socket...")
        sock.write('quit')
        
        
def BoardArrayWorker(GPIO,running:Event,push_to_queue,output_queue,poll_interval=0.03):
    '''
    thread Owns BoardSensorArray which owns the SPI bus +  4x cs pin. Is responsible for SPI cleanup.

    '''
    board_sensor_array = BoardSensorArray(GPIO=GPIO)
    # prev_board_value = board_sensor_array._read_all()
    # while running.is_set():
    #     #if not push_to_queue.is_set():
    #     push_to_queue.wait()
    #     new_board = board_sensor_array._read_all()
    #     if not np.array_equal(new_board, prev_board_value):
    #         board_event = diff_board_array_to_event(prev_board_value,new_board)
    #         if board_event is None:
    #             #handle board_array_to_uci errors.
    #             continue
    #         prev_board_value = new_board
    #         #if push_to_queue.is_set():
    #         output_queue.put(board_event)
    #         print(f'board event detected:{board_event}') #   
    #     time.sleep(poll_interval)    
    while running.is_set():
        if push_to_queue.is_set() is False:
            first:bool = True
        push_to_queue.wait() 
        new_board = board_sensor_array._read_all()
        if first:
            prev_board = new_board
            first = False
        if np.array_equal(prev_board, new_board):
            continue
        board_event = diff_board_array_to_event(prev_board,new_board)
        if board_event is None:
            #handle board_array_to_uci errors.
            continue
        prev_board = new_board
        output_queue.put(board_event)
        print(f'board event detected:{board_event}') #
        time.sleep(poll_interval)


    board_sensor_array.close_spi()

def ButtonWorker(GPIO:GPIO,queue:Queue,running:Event):
    GPIO.add_event_detect(BoardPin.white_button, GPIO.RISING)  
    GPIO.add_event_detect(BoardPin.black_button, GPIO.RISING)
    while running.is_set():
        inst = [None] * 2
        if GPIO.event_detected(BoardPin.white_button):
            inst[0] = True
            update = True
        if GPIO.event_detected(BoardPin.white_button):
            inst[1] = True
            update = True
        if update:
            queue.put(inst)


#TODO: replace with 2 GPIO buttons PULLUP on each side of chessboard
def KeyboardWorker(key:str,output_queue):
    if key == 'z':
        print('complete action')
        output_queue.put('completed action')

    elif key == 'q':
        output_queue.put('quit')
    

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-a",action='store_true',default=False,help = "enable aws logging")
    args = parser.parse_args()
    chess_game = Game(logging = args.a)
    chess_game.run()


if __name__ == "__main__":
    main()
    
    
        
