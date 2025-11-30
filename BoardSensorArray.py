
from Drivers.MCP23S17 import MCP23S17
from Drivers.MCP23S17 import SpiBus

import time
#import RPi.GPIO as GPIO
import numpy as np 
from collections import OrderedDict

import atexit
#from icecream import ic

'''
    wrapper of the generic MCP23S17 driver.
    adds software chip enable pins for even more spi addressing.
    
    Board is divided to 4 sections of MCP23S17. Each maps to a different
    chip enable GPIO pin shown below:


    ♜♞♝♛♚♝♞♜  top  -> 
    ♟♟♟♟♟♟♟♟

    ▒█▒█▒█▒█         midtop ->
    █▒█▒█▒█▒

    ▒█▒█▒█▒█         midbottom -> 33
    █▒█▒█▒█▒          

    ♙♙♙♙♙♙♙     bottom -> 37
    ♖♘♗♕♔♗♘♖     
    a b

tab symbol:
	
	
	
'''
class BoardSensorArray:   
   # CS_PIN_BANK = [BOTTOM_CS_PIN, MIDBOTTOM_CS_PIN]
    MCP_INSTANCES = ['MIDBOTTOM_CS_PIN','BOTTOM_CS_PIN']
    CS_PIN_BANK = [33,37]

    def __init__(self,GPIO):
        self.GPIO = GPIO
        # shared spi bus
        self.spi_bus = SpiBus(gpio=GPIO)
        self.prev_board_state = None

        self.MCP23S17_dict = OrderedDict()
        for name,pin in zip(BoardSensorArray.MCP_INSTANCES, BoardSensorArray.CS_PIN_BANK):
            self.MCP23S17_dict[name] = MCP23S17(name,self.spi_bus,GPIO,pin_cs=pin)

        #self.mcp1 = MCP23S17(self.spi_bus,GPIO,pin_cs=37)
        #self.mcp2 = MCP23S17(self.spi_bus,GPIO,pin_cs=33)
        

        # cs_Pin setup. all GPIO must be set to high before writing to any 
        # registers to prevent rewriting the same mcp23s17 device.
        for inst in self.MCP23S17_dict.values():
            inst.setupGPIO()
    
        #self.mcp1.setupGPIO()
        #self.mcp2.setupGPIO()
        
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
            [a2,b2,c2,d2,e2,f2,g2,h2],
            [a1,b1,c1,d1,e1,f1,g1,h1]
        ]
                
    def _read_all(self)->np.array:
        result = []
        for name, mcp_inst in self.MCP23S17_dict.items():
            quarter_board = self._read_MCP23S17(mcp_inst)
            #print(name)
            #print(quarter_board)
            result.extend(quarter_board)
            
         #result = result[::-1]
        #print(result)
        
        return np.array(result)
    
    def _read_MCP23S17(self,mcp_instance):
        '''
        
        '''
        state = mcp_instance.readGPIO()
        quarter_board = self._bits_2_board_mapping(state)
        return quarter_board
    
# def test_MCP23S17():
#     mcp = MCP23S17(device_id=0x00,gpio = GPIO)
#     mcp.open_spi_bus()

#     for x in range(16):
#         mcp.setDirection(x, mcp.DIR_INPUT)
#         mcp.setPullupMode(x,mcp.PULLUP_DISABLED)
    
#     while True:
#         print(mcp.readGPIO())
#         time.sleep(1)

#     mcp.close()
    


if __name__ == "__main__":
    import RPi.GPIO as GPIO

    #GPIO module setup
    GPIO.setmode(GPIO.BOARD)

    board_sensor_array = BoardSensorArray(GPIO=GPIO) 
    try:
        while True:
            results = board_sensor_array._read_all()
            # for sublist in reversed(results):
               #  print(sublist)
            print(results)
				
            time.sleep(1)
			
    except KeyboardInterrupt:
        print("closing...")
        GPIO.cleanup()


