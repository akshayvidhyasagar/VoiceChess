import os
import shutil
import chess
import chess.engine

STOCKFISH_ERROR_MSG = """
[Error] Stockfish binary not found.
To play against the computer, you must have Stockfish installed.

Installation Instructions:
- macOS:
    brew install stockfish
- Linux (Ubuntu/Debian):
    sudo apt-get install stockfish
- Windows:
    1. Download the Stockfish binary from https://stockfishchess.org/download/
    2. Extract the executable to a directory.
    3. Add the path to the executable to your system's PATH, or set the STOCKFISH_PATH environment variable:
       set STOCKFISH_PATH=C:\\path\\to\\stockfish.exe
"""

def find_stockfish():
    """Locate the Stockfish binary on the system.

    Returns the absolute path to the executable, or raises FileNotFoundError.
    """
    # 1. Check STOCKFISH_PATH environment variable
    env_path = os.getenv("STOCKFISH_PATH")
    if env_path:
        if os.path.exists(env_path) and os.path.isfile(env_path):
            return env_path
        # Also try expanding path if relative/user path
        expanded = os.path.abspath(os.path.expanduser(env_path))
        if os.path.exists(expanded) and os.path.isfile(expanded):
            return expanded

    # 2. Check local bin/stockfish
    local_path = os.path.join(os.getcwd(), "bin", "stockfish")
    if os.path.exists(local_path) and os.path.isfile(local_path):
        return local_path

    # Also try stockfish.exe on Windows in local bin
    local_win_path = os.path.join(os.getcwd(), "bin", "stockfish.exe")
    if os.path.exists(local_win_path) and os.path.isfile(local_win_path):
        return local_win_path

    # 3. Check system PATH
    sys_path = shutil.which("stockfish")
    if sys_path:
        return sys_path
    
    # Try common Windows names on PATH
    sys_win_path = shutil.which("stockfish.exe")
    if sys_win_path:
        return sys_win_path

    # 4. Check common macOS paths (Homebrew / MacPorts)
    mac_paths = [
        "/opt/homebrew/bin/stockfish",
        "/usr/local/bin/stockfish",
        "/opt/homebrew/bin/stockfish-chess"
    ]
    for p in mac_paths:
        if os.path.exists(p) and os.path.isfile(p):
            return p

    raise FileNotFoundError(STOCKFISH_ERROR_MSG)


class StockfishBot:
    """Wrapper around the Stockfish UCI chess engine."""

    def __init__(self, elo=1600):
        self.path = find_stockfish()
        self.elo = max(100, min(3200, elo))
        self.engine = None
        self.start()

    def start(self):
        """Start the Stockfish UCI engine subprocess."""
        if self.engine is not None:
            return
        
        self.engine = chess.engine.SimpleEngine.popen_uci(self.path)
        self.configure_elo()

    def configure_elo(self):
        """Set the engine's ELO rating / strength options."""
        if not self.engine:
            return

        try:
            # Attempt to set the standard UCI Elo options
            self.engine.configure({
                "UCI_LimitStrength": True,
                "UCI_Elo": self.elo
            })
        except Exception:
            # Fall back to Skill Level if UCI_LimitStrength/UCI_Elo are not supported.
            # Stockfish Skill Level ranges from 0 (e.g. ~800 Elo) to 20 (max/3000+ Elo).
            # We map ELO linearly: Skill = (elo - 800) / 100
            skill_level = max(0, min(20, int((self.elo - 800) / 100)))
            try:
                self.engine.configure({"Skill Level": skill_level})
            except Exception as e:
                # If even Skill Level fails, log it or print warning but continue
                print(f"[Warning] Could not configure engine strength option: {e}")

    def get_move(self, board, time_limit=0.5, depth_limit=15):
        """Get the best move from the engine for the current board state.

        Args:
            board: A chess.Board instance.
            time_limit: Max thinking time in seconds.
            depth_limit: Max calculation depth.

        Returns:
            A chess.Move instance.
        """
        if not self.engine:
            self.start()
        
        limit = chess.engine.Limit(time=time_limit, depth=depth_limit)
        result = self.engine.play(board, limit)
        return result.move

    def close(self):
        """Cleanly close the engine subprocess."""
        if self.engine:
            self.engine.quit()
            self.engine = None

    def __enter__(self):
        self.start()
        return self
   
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
