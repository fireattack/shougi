from flask import Flask, render_template
from flask_socketio import SocketIO, emit

from flask_cors import CORS

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
CORS(app)
socketio = SocketIO(app, cors_allowed_origins='*')

game_state = {}

@app.route('/')
def index():
    return render_template('index.html')  # Render the Tic-Tac-Toe HTML page

def check_winner(game_state):
    # Type 2 is the king.
    # if it is captured, the game is over
    x_king_exists = False
    o_king_exists = False

    # Check if the king is captured
    for row in game_state['board']:
        for cell in row:
            if cell and cell['type'] == '2':
                if cell['faction'] == 'X':
                    # if X king is at the bottom row in the opponent's turn, X wins
                    if row == 3 and game_state['current_player'] == 'O':
                        return 'X'
                    x_king_exists = True
                elif cell['faction'] == 'O':
                    if row == 0 and game_state['current_player'] == 'X':
                        return 'O'
                    o_king_exists = True
    # Determine the winner based on the number of pieces remaining
    if not x_king_exists:
        return 'O'
    elif not o_king_exists:
        return 'X'
    else:
        return None  # No winner yet

def check_draw(board):
    # Check for a draw on the board
    return all([cell != '' for cell in board])

def initialize_game_state():
    # Create an empty 3x4 board
    # Represent the board as a 2D list, each cell can be None or a dictionary with piece info
    board = [[None for _ in range(3)] for _ in range(4)]

    # Define initial positions for the pieces
    # Top faction (X) pieces
    board[0][0] = {'type': '1', 'faction': 'X'}
    board[0][1] = {'type': '2', 'faction': 'X'}
    board[0][2] = {'type': '3', 'faction': 'X'}
    board[1][1] = {'type': '4', 'faction': 'X'}

    # Bottom faction (O) pieces
    board[2][1] = {'type': '4', 'faction': 'O'}
    board[3][0] = {'type': '3', 'faction': 'O'}
    board[3][1] = {'type': '2', 'faction': 'O'}
    board[3][2] = {'type': '1', 'faction': 'O'}

    # Other game state variables
    game_state = {
        'board': board,
        'current_player': 'X',  # X starts the game
        'game_over': False,
        'winner': None
    }

    return game_state

def reset_game():
    global game_state
    game_state = initialize_game_state()


def is_valid_move(src, dst, player, game_state):
    # Extract row and column for source and destination
    src_row = src['row']
    src_col = src['col']
    dst_row = dst['row']
    dst_col = dst['col']

    # Check if the move is within bounds of the board
    if not (0 <= dst_row < 4 and 0 <= dst_col < 3):
        return False

    # Check if the source cell contains the player's piece
    src_piece = game_state['board'][src_row][src_col]
    if not src_piece or src_piece['faction'] != player:
        return False

    # Calculate row and column differences
    row_diff = dst_row - src_row
    col_diff = dst_col - src_col

    # Type-specific movement rules
    if src_piece['type'] == '1':
        # Type 1 can move in all straight directions by 1
        if abs(row_diff) + abs(col_diff) != 1:
            return False

    elif src_piece['type'] == '2':
        # Type 2 can move in all 8 directions by 1
        if abs(row_diff) > 1 or abs(col_diff) > 1:
            return False

    elif src_piece['type'] == '3':
        # Type 3 can move in all 4 diagonal directions by 1
        if abs(row_diff) != 1 or abs(col_diff) != 1:
            return False

    elif src_piece['type'] == '4':
        # Type 4 can only move forward (down for X, up for O) by 1
        if player == 'X' and row_diff != 1:
            return False
        elif player == 'O' and row_diff != -1:
            return False
        elif col_diff != 0:
            return False
    elif src_piece['type'] == '5':
        # Type 5 can move forward, forward diagonal, left, right and backward (but not backward diagonal) by 1
        if player == 'X' and row_diff == -1 and col_diff != 0:
            return False
        elif player == 'O' and row_diff == 1 and col_diff != 0:
            return False
        elif abs(row_diff) > 1 or abs(col_diff) > 1:
            return False

    # Check if the destination cell is not occupied by a friendly piece
    dst_piece = game_state['board'][dst_row][dst_col]
    if dst_piece and dst_piece['faction'] == player:
        return False

    return True

def make_move(src, dst, game_state):
    src_row = src['row']
    src_col = src['col']
    dst_row = dst['row']
    dst_col = dst['col']

    # Move the piece from src to dst
    piece = game_state['board'][src_row][src_col]

    # upgrade type4 to type5, if it reaches the other side
    if piece['type'] == '4' and dst_row == 3 and piece['faction'] == 'X':
        piece['type'] = '5'
    elif piece['type'] == '4' and dst_row == 0 and piece['faction'] == 'O':
        piece['type'] = '5'

    game_state['board'][dst_row][dst_col] = piece
    game_state['board'][src_row][src_col] = None


def switch_turns(game_state):
    current_player = game_state['current_player']
    game_state['current_player'] = 'O' if current_player == 'X' else 'X'


def check_for_capture(dst, game_state):
    dst_row = dst['row']
    dst_col = dst['col']

    # Get the piece at the destination cell
    dst_piece = game_state['board'][dst_row][dst_col]

    # If the destination cell has an opponent's piece, it is captured
    if dst_piece and dst_piece['faction'] != game_state['current_player']:
        # Remove the captured piece from the board
        game_state['board'][dst_row][dst_col] = None

# Socket event for resetting the game
@socketio.on('reset_game')
def handle_reset_game():
    reset_game()
    emit('game_state', game_state, broadcast=True)

# Assuming you have a function to initialize the game state
game_state = initialize_game_state()

@socketio.on('make_move')
def handle_make_move(data):
    src = data['src']
    dst = data['dst']
    player = data['player']

    if is_valid_move(src, dst, player, game_state):
        make_move(src, dst, game_state)
        check_for_capture(dst, game_state)
        winner = check_winner(game_state)
        if winner:
            game_state['game_over'] = True
            game_state['winner'] = winner
        else:
            switch_turns(game_state)
        emit('game_state', game_state, broadcast=True)
    else:
        # Optionally send an error message back to the player
        emit('move_error', {'message': 'Invalid move'})

@socketio.on('request_initial_state')
def handle_initial_state_request():
    # Assuming game_state is your global or accessible game state variable
    emit('game_state', game_state)

if __name__ == '__main__':
    socketio.run(app, debug=True, port=5000)