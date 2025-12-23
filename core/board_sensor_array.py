
from Drivers.MCP23S17 import MCP23S17
from Drivers.MCP23S17 import SpiBus

import time
#import RPi.GPIO as GPIO
import numpy as np 
from collections import OrderedDict

import atexit
#from icecream import ic

'''
    Owns the SPI bus.
    
    wrapper of the generic MCP23S17 driver.
    adds software chip enable pins for even more spi addressing.
    
    Board is divided to 4 sections of MCP23S17. Each maps to a different
    chip enable GPIO pin shown below:


    ♜♞♝♛♚♝♞♜  top  -> 40
    ♟♟♟♟♟♟♟♟

    ▒█▒█▒█▒█         midtop -> 38
    █▒█▒█▒█▒

    ▒█▒█▒█▒█         midbottom -> 33
    █▒█▒█▒█▒          

    ♙♙♙♙♙♙♙     bottom -> 37
    ♖♘♗♕♔♗♘♖     
    a b

'''
class BoardSensorArray:   

    MCP_INSTANCES = ['BOTTOM_CS_PIN', 'MIDBOTTOM_CS_PIN', 'MIDTOP_CS_PIN', 'TOP_CS_PIN']
    CS_PIN_BANK = [37,33,36,40]

    def __init__(self,GPIO):
        self.GPIO = GPIO
        # shared spi bus
        self.spi_bus = SpiBus(gpio=GPIO)
        self.prev_board_state = None

        self.MCP23S17_dict = OrderedDict()
        for name,pin in zip(BoardSensorArray.MCP_INSTANCES, BoardSensorArray.CS_PIN_BANK):
            self.MCP23S17_dict[name] = MCP23S17(name,self.spi_bus,GPIO,pin_cs=pin)

        # cs_Pin setup. all GPIO must be set to high before writing to any 
        # registers to prevent rewriting the same mcp23s17 device.
        for inst in self.MCP23S17_dict.values():
            inst.setupGPIO()
        
        for inst in self.MCP23S17_dict.values():
            inst.init_MCP23S17()
     
    @staticmethod
    def _bits_2_board_mapping(bits:int):
        '''
        change 2^16 integer reported from self.mcp.readGPIO() 
        to 2 dimension list of size 2*8.
        '''        
        #print(bits) 
        a1 = 1 - ((bits >> 7) & 1)
        b1 = 1 - ((bits >> 6) & 1)
        c1 = 1 - ((bits >> 5) & 1)    
        d1 = 1 - ((bits >> 4) & 1)
        e1 = 1 - ((bits >> 3) & 1)    
        f1 = 1 - ((bits >> 2) & 1)
        g1 = 1 - ((bits >> 1) & 1)    
        h1 = 1 - ((bits >> 0) & 1)

        a2 = 1 - ((bits >> 8) & 1)    
        b2 = 1 - ((bits >> 9) & 1)
        c2 = 1 - ((bits >> 10) & 1)    
        d2 = 1 - ((bits >> 11) & 1)
        e2 = 1 - ((bits >> 12) & 1)    
        f2 = 1 - ((bits >> 13) & 1)
        g2 = 1 - ((bits >> 14) & 1)    
        h2 = 1 - ((bits >> 15) & 1)

        return [
            [h2,g2,f2,e2,d2,c2,b2,a2],
            [h1,g1,f1,e1,d1,c1,b1,a1]
        ]
                
    def _read_all(self)->np.array:
        result = []
        for name, mcp_inst in self.MCP23S17_dict.items():
            quarter_board = self._read_MCP23S17(mcp_inst)
            #print(name)
            #print(quarter_board)
            result.extend(quarter_board)
        return np.array(result)
    
    def pretty_print(self, array) -> None:
        print("-------------------")
        printed = np.flipud(array)
        for row in printed:
            print(" ".join(map(str, row)))

        print("-------------------")

    def _read_MCP23S17(self,mcp_instance):
        state = mcp_instance.readGPIO()
        quarter_board = self._bits_2_board_mapping(state)
        return quarter_board
    
    def close_spi(self):
        self.spi_bus.close()
    

if __name__ == "__main__":
    import RPi.GPIO as GPIO

    #GPIO module setup
    GPIO.setmode(GPIO.BOARD)

    board_sensor_array = BoardSensorArray(GPIO=GPIO) 
    try:
        while True:
            results = board_sensor_array._read_all()            
            board_sensor_array.pretty_print(results)

            time.sleep(1)

    except KeyboardInterrupt:
        print("closing...")
        GPIO.cleanup()


