# All SocketIO code from https://github.com/miguelgrinberg/Flask-SocketIO
# under MIT License


from colour import colour
import os
from threading import Lock

from flask import Flask, render_template, make_response, request, session
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_socketio import close_room, rooms, disconnect


ROOT_CONTEXT = os.environ.get('ROOT_CONTEXT', '/')
DEBUG = bool(os.environ.get('DEBUG', False))


app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
socketio = SocketIO(app, engineio_logger=DEBUG, logger=DEBUG)
thread = None
thread_lock = Lock()


@app.route(ROOT_CONTEXT)
def docker_debug():
    with open(os.environ.get("WWW_DATA", "helloworld.txt")) as f:
        data = f.read()
    response = make_response(render_template('docker_debug.j2',
                                             colour=colour, data=data,
                                             environs=os.environ,
                                             headers=request.headers))
    response.headers['Cache-Control'] = 'max-age=0'
    return response


@app.route(f'{ROOT_CONTEXT}/ws', methods=['GET', 'POST'])
def websocket_test():
    return make_response(render_template('ws.j2',
                                         namespace=f'{ROOT_CONTEXT}/ws'))


def background_thread():
    """Example of how to send server generated events to clients."""
    count = 0
    while True:
        socketio.sleep(10)
        count += 1
        socketio.emit('my_response',
                      {'data': 'Server generated event', 'count': count},
                      namespace=f'{ROOT_CONTEXT}/ws')


@socketio.on('my_event', namespace=f'{ROOT_CONTEXT}/ws')
def test_message(message):
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my_response',
         {'data': message['data'], 'count': session['receive_count']})


@socketio.on('my_broadcast_event', namespace=f'{ROOT_CONTEXT}/ws')
def test_broadcast_message(message):
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my_response',
         {'data': message['data'], 'count': session['receive_count']},
         broadcast=True)


@socketio.on('join', namespace=f'{ROOT_CONTEXT}/ws')
def join(message):
    join_room(message['room'])
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my_response',
         {'data': 'In rooms: ' + ', '.join(rooms()),
          'count': session['receive_count']})


@socketio.on('leave', namespace=f'{ROOT_CONTEXT}/ws')
def leave(message):
    leave_room(message['room'])
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my_response',
         {'data': 'In rooms: ' + ', '.join(rooms()),
          'count': session['receive_count']})


@socketio.on('close_room', namespace=f'{ROOT_CONTEXT}/ws')
def close(message):
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my_response', {'data': 'Room ' + message['room'] + ' is closing.',
                         'count': session['receive_count']},
         room=message['room'])
    close_room(message['room'])


@socketio.on('my_room_event', namespace=f'{ROOT_CONTEXT}/ws')
def send_room_message(message):
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my_response',
         {'data': message['data'], 'count': session['receive_count']},
         room=message['room'])


@socketio.on('disconnect_request', namespace=f'{ROOT_CONTEXT}/ws')
def disconnect_request():
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my_response',
         {'data': 'Disconnected!', 'count': session['receive_count']})
    disconnect()


@socketio.on('my_ping', namespace=f'{ROOT_CONTEXT}/ws')
def ping_pong():
    emit('my_pong')


@socketio.on('connect', namespace=f'{ROOT_CONTEXT}/ws')
def test_connect():
    global thread
    with thread_lock:
        if thread is None:
            thread = socketio.start_background_task(background_thread)
    emit('my_response', {'data': 'Connected', 'count': 0})


@socketio.on('disconnect', namespace=f'{ROOT_CONTEXT}/ws')
def test_disconnect():
    print('Client disconnected', request.sid)


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', debug=DEBUG)
