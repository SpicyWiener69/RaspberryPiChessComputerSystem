import chess
import chess.engine


class ChessEngineWrapper:
        
    def __init__(STOCKFISH_PATH = "/usr/games/stockfish"):
        # Initialize engine
        self.engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)


    def play(board):
        
        # Create a board
        board = chess.Board()  # Start from standard position

result = engine.play(board, chess.engine.Limit(time=3))  # 0.1 sec per move
print("Stockfish move:", result.move)

# Apply the move to the board
board.push(result.move)
print(board)

# Optional: evaluate current position
info = engine.analyse(board, chess.engine.Limit(time=0.1))
print("Evaluation:", info["score"])

# Close the engine
engine.quit()



if __name__ == "__main__":
    