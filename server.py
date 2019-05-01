# All SocketIO code from https://github.com/miguelgrinberg/Flask-SocketIO
# under MIT License


from colour import colour
import os
from threading import Lock

from flask import Flask, render_template, make_response, request, session, Blueprint
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_socketio import close_room, rooms, disconnect


DEBUG = bool(os.environ.get('DEBUG', False))


app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
socketio = SocketIO(app, engineio_logger=DEBUG, logger=DEBUG)
thread = None
thread_lock = Lock()


bp = Blueprint('docker-debug', __name__,
               template_folder='templates',
               static_folder='static')


@bp.route('/')
def docker_debug():
    with open(os.environ.get("WWW_DATA", "helloworld.txt")) as f:
        data = f.read()
    response = make_response(render_template('docker_debug.j2',
                                             colour=colour, data=data,
                                             environs=os.environ,
                                             headers=request.headers))
    response.headers['Cache-Control'] = 'max-age=0'
    return response


@bp.route('/ws', methods=['GET', 'POST'])
def websocket_test():
    return make_response(render_template('ws.j2',
                                         namespace='/ws'))


app.register_blueprint(bp, url_prefix=os.environ.get('ROOT_CONTEXT', '/'))


def background_thread():
    """Example of how to send server generated events to clients."""
    count = 0
    while True:
        socketio.sleep(10)
        count += 1
        socketio.emit('my_response',
                      {'data': 'Server generated event', 'count': count},
                      namespace='/ws')


@socketio.on('my_event', namespace='/ws')
def test_message(message):
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my_response',
         {'data': message['data'], 'count': session['receive_count']})


@socketio.on('my_broadcast_event', namespace='/ws')
def test_broadcast_message(message):
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my_response',
         {'data': message['data'], 'count': session['receive_count']},
         broadcast=True)


@socketio.on('join', namespace='/ws')
def join(message):
    join_room(message['room'])
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my_response',
         {'data': 'In rooms: ' + ', '.join(rooms()),
          'count': session['receive_count']})


@socketio.on('leave', namespace='/ws')
def leave(message):
    leave_room(message['room'])
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my_response',
         {'data': 'In rooms: ' + ', '.join(rooms()),
          'count': session['receive_count']})


@socketio.on('close_room', namespace='/ws')
def close(message):
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my_response', {'data': 'Room ' + message['room'] + ' is closing.',
                         'count': session['receive_count']},
         room=message['room'])
    close_room(message['room'])


@socketio.on('my_room_event', namespace='/ws')
def send_room_message(message):
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my_response',
         {'data': message['data'], 'count': session['receive_count']},
         room=message['room'])


@socketio.on('disconnect_request', namespace='/ws')
def disconnect_request():
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my_response',
         {'data': 'Disconnected!', 'count': session['receive_count']})
    disconnect()


@socketio.on('my_ping', namespace='/ws')
def ping_pong():
    emit('my_pong')


@socketio.on('connect', namespace='/ws')
def test_connect():
    global thread
    with thread_lock:
        if thread is None:
            thread = socketio.start_background_task(background_thread)
    emit('my_response', {'data': 'Connected', 'count': 0})


@socketio.on('disconnect', namespace='/ws')
def test_disconnect():
    print('Client disconnected', request.sid)


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', debug=DEBUG)
