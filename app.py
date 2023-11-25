import random

from flask import Flask, render_template
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_cors import CORS
from game import *

from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

app.config['SECRET_KEY'] = 'your_secret_key'
CORS(app)
socketio = SocketIO(app, cors_allowed_origins='*')

room_states = {}

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('join')
def on_join(data):
    room = data['room']
    if not room in room_states:
        room_states[room] = initialize_game_state()
    join_room(room)
    state = room_states[room]
    emit('room_info', {'room': room, 'state': state}, room=room)

# Socket event for resetting the game
@socketio.on('reset_game')
def handle_reset_game(data):
    room = data['room']
    room_states[room] = initialize_game_state()
    emit('game_state', room_states[room], room=room)

@socketio.on('make_move')
def handle_make_move(data):
    room = data['room']
    src = data['src']
    dst = data['dst']
    player = data['player']

    game_state = room_states[room]

    validality = is_valid_move(src, dst, player, game_state)
    if validality == True:
        make_move(src, dst, game_state)
        winner = check_winner(game_state)
        if winner:
            game_state['game_over'] = True
            game_state['winner'] = winner
        else:
            switch_turns(game_state)
        emit('game_state', game_state, room=room)
    else:
        # Optionally send an error message back to the player
        emit('move_error', {'message': validality})

@socketio.on('get_state')
def handle_get_state(data):
    room = data['room']
    emit('game_state', room_states[room], room=room)

@socketio.on('get_valid_moves')
def handle_get_valid_moves(data):
    src = data['src']
    player = data['player']
    room = data['room']
    game_state = room_states[room]
    valid_moves = get_valid_moves(src, player, game_state)
    emit('valid_moves', valid_moves)

if __name__ == '__main__':
    socketio.run(app, debug=True, port=5000)