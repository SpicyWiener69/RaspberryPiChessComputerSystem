### Chess Computer System based on a Raspberry Pi

## Folder Descriptions
```
.
├── UI:    Chess UI frontend. Allows players to adjust game settings.
├── core:  program entry point. Handles game logic.
├── ChessBoardPCB: A PCB board with hall effect sensors designed to sense the position of a chess game.     
└── hardware: BOM, 3d design files of the system 
```

## setup the python env:

Navigate to Project Directory
```
cd RaspberryPiChessComputerSystem/
```
Create Virtual Environment
```
python -m venv venv
```
Activate Virtual Environment
```
source venv/bin/activate
```
Install Dependencies
```
pip install -r core/requirements.txt
```


