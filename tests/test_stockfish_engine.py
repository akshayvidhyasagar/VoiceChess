import os
import pytest
import chess
from stockfish_engine import find_stockfish, StockfishBot, STOCKFISH_ERROR_MSG


def test_find_stockfish():
    # Since we installed Stockfish on the system, this should find it successfully.
    path = find_stockfish()
    assert os.path.exists(path)
    assert os.path.isfile(path)


def test_find_stockfish_not_found(monkeypatch):
    # Mock STOCKFISH_PATH to a nonexistent path and clear PATH/common paths
    monkeypatch.setenv("STOCKFISH_PATH", "/nonexistent/stockfish_bin")

    # Mock shutil.which AND os.path.exists/isfile within the engine module so no
    # fallback path (hardcoded common paths, local bin, etc.) is found.
    monkeypatch.setattr("stockfish_engine.shutil.which", lambda x: None)
    monkeypatch.setattr("stockfish_engine.os.path.exists", lambda x: False)
    monkeypatch.setattr("stockfish_engine.os.path.isfile", lambda x: False)

    # We expect FileNotFoundError with the custom STOCKFISH_ERROR_MSG
    with pytest.raises(FileNotFoundError) as exc_info:
        find_stockfish()
    assert STOCKFISH_ERROR_MSG in str(exc_info.value)


def test_stockfish_bot_initialization():
    bot = StockfishBot(elo=1500)
    assert bot.elo == 1500
    assert bot.engine is not None
    bot.close()


def test_stockfish_bot_clamping():
    # ELO should clamp between 100 and 3200
    bot1 = StockfishBot(elo=50)
    assert bot1.elo == 100
    bot1.close()

    bot2 = StockfishBot(elo=4000)
    assert bot2.elo == 3200
    bot2.close()


def test_stockfish_bot_get_move():
    bot = StockfishBot(elo=1200)
    board = chess.Board()
    
    move = bot.get_move(board, time_limit=0.1, depth_limit=5)
    assert isinstance(move, chess.Move)
    # The move must be legal
    assert move in board.legal_moves
    bot.close()


def test_stockfish_bot_context_manager():
    with StockfishBot(elo=1600) as bot:
        assert bot.engine is not None
        board = chess.Board()
        move = bot.get_move(board, time_limit=0.1, depth_limit=5)
        assert move in board.legal_moves
    # Outside context, engine should be closed/None
    assert bot.engine is None
