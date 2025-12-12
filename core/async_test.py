

# import asyncio
# import time

# q = asyncio.Queue()

# def read_sensor():
#     t = 0.5
#     time.sleep(t)
#     return t

# async def sync_sensor():
#     loop = asyncio.get_running_loop()

#     while True:
#         t = await loop.run_in_executor(None, read_sensor)
#         print("sensor:", t)
#         await q.put(t)




# async def main():
#     # start background sensor task
#     asyncio.create_task(sync_sensor())

#     while True:
#         t = await q.get()     # waits asynchronously
#         print("queue:", t)

# asyncio.run(main())
# from dataclasses import dataclass, field
# import chess

# @dataclass
# class GameState:
#     isrunning: bool = False
#     Turn:str =  "white"
#     Computer_playing:bool = False
#     Computer_side:str = None
#     #@dataclasses default to class variables. Factory is needed
#     board: chess.Board = field(default_factory=chess.Board)
    
# state = GameState()



from enum import Enum

class GameState:
    class InputState(Enum):
        WAITING_FOR_MOVE = 1
        AWAITING_RETRY   = 2
    
    def __init__(self):

        self.input_state = GameState.InputState.WAITING_FOR_MOVE
        self.is_game_running: bool = True
        self.is_sensor_array_running:bool = True
        self.Turn:str =  "white"
        self.Computer_playing:bool = False
        self.Computer_side:str = None
        self.update_display_flag:bool = False
    
    def check(self):
        return self.input_state == GameState.InputState.WAITING_FOR_MOVE
        
state = GameState()
print(state.is_game_running)
print(state.input_state)
state.check()


# from enum import Enum

# class GameState:

#     class InputState(Enum):
#         WAITING_FOR_MOVE = 1
#         AWAITING_RETRY   = 2

#     def __init__(self):
#         self.input_state = GameState.InputState.WAITING_FOR_MOVE
#         self.is_game_running: bool = True
#         self.is_sensor_array_running: bool = True
#         self.Turn: str = "white"
#         self.Computer_playing: bool = False
#         self.Computer_side: str | None = None
#         self.update_display_flag: bool = False

#     def check(self):
#         return self.input_state == GameState.InputState.WAITING_FOR_MOVE