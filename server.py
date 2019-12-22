# All SocketIO code from https://github.com/miguelgrinberg/Flask-SocketIO
# under MIT License


from colour import colour
import os
import random
from threading import Lock
import time

from flask import Flask, render_template, make_response, request, session, Blueprint
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_socketio import close_room, rooms, disconnect
from flask_opentracing import FlaskTracing
import zipkin_ot

DEBUG = bool(os.environ.get('DEBUG', False))


app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
socketio = SocketIO(app, engineio_logger=DEBUG, logger=DEBUG)
thread = None
thread_lock = Lock()


bp = Blueprint('docker-debug', __name__,
               template_folder='templates',
               static_folder='static')

TRACING_HOST = os.environ.get('TRACING_HOST')
TRACING_PORT = os.environ.get('TRACING_PORT')
TRACING_SAMPLE_RATE = float(os.environ.get('TRACING_SAMPLE_RATE', 0))

open_tracer = zipkin_ot.Tracer(
    service_name='docker-debug',
    collector_host=TRACING_HOST,
    collector_port=TRACING_PORT,
    verbosity=2,
)
tracing = FlaskTracing(open_tracer)

@bp.route('/')
@tracing.trace()
def index():
    with open(os.environ.get("WWW_DATA", "helloworld.txt")) as f:
        data = f.read()
    parent_span = tracing.get_span()
    with open_tracer.start_active_span('/', child_of=parent_span) as scope:
        scope.span.set_tag('component', 'flask')
        response = make_response(render_template('docker_debug.j2',
                                                 colour=colour, data=data,
                                                 environs=os.environ,
                                                 headers=request.headers))
        response.headers['Cache-Control'] = 'max-age=0'
        return response


@bp.route('/sleep/<count>')
@tracing.trace()
def sleep(count):
    parent_span = tracing.get_span()
    with open_tracer.start_active_span('/sleep', child_of=parent_span) as scope:
        scope.span.set_tag('component', 'flask')
        scope.span.set_tag('sleep', count)
        time.sleep(int(count))
        response = make_response(render_template('docker_debug.j2',
                                                 colour=colour,
                                                 environs=os.environ,
                                                 headers=request.headers))
        response.headers['Cache-Control'] = 'max-age=0'
        return response


@bp.route('/random/<code>/<percent>')
@tracing.trace()
def random_code(code, percent):
    parent_span = tracing.get_span()
    with open_tracer.start_active_span('/random', child_of=parent_span) as scope:
        scope.span.set_tag('code', code)
        scope.span.set_tag('percent', percent)
        scope.span.set_tag('component', 'flask')
        if int(percent) <= random.randint(1, 100):
            result = ("Oh No!", int(code))
        else:
            result= ("Yay", 200)
        response = make_response(*result)
        return response


@bp.route('/ping')
def ping():
    response = make_response('pong')
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
