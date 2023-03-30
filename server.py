# All SocketIO code from https://github.com/miguelgrinberg/Flask-SocketIO
# under MIT License


from colour import colour
from version import version
import opentelemetry
import os
import random
import string
from threading import Lock
import time
import logging

from flask import Flask, render_template, make_response, request, session, Blueprint
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_socketio import close_room, rooms, disconnect
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

DEBUG = bool(os.environ.get('DEBUG', False))
PORT = int(os.environ.get('PORT', 5000))


app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
FlaskInstrumentor().instrument_app(app)
socketio = SocketIO(app, engineio_logger=DEBUG, logger=DEBUG)
thread = None
thread_lock = Lock()


bp = Blueprint('docker-debug', __name__,
               template_folder='templates',
               static_folder='static')

TRACING_HOST = os.environ.get('TRACING_HOST')
TRACING_PORT = os.environ.get('TRACING_PORT')

resource = Resource(attributes={
    "service.name": "docker-debug"
})

opentelemetry.trace.set_tracer_provider(TracerProvider(resource=resource))
tracer = opentelemetry.trace.get_tracer(__name__)

if TRACING_HOST and TRACING_PORT:
    otlp_exporter = OTLPSpanExporter(endpoint=f"http://{TRACING_HOST}:{TRACING_PORT}", insecure=True)
    span_processor = BatchSpanProcessor(otlp_exporter)
    opentelemetry.trace.get_tracer_provider().add_span_processor(span_processor)

# disable werkzeug request logs
logging.getLogger('werkzeug').disabled = True


@app.before_request
def log_request():
    app.logger.debug('===================================================')
    app.logger.debug(f'{request.method} {request.url}')
    app.logger.debug(request.headers)
    app.logger.debug(request.data or request.form)
    app.logger.debug('')
    return None


@bp.route('/')
def index():
    with open(os.environ.get("WWW_DATA", "helloworld.txt")) as f:
        data = f.read()
    response = make_response(render_template('docker_debug.j2',
                                             colour=colour, data=data,
                                             environs=os.environ,
                                             headers=request.headers))
    response.headers['Cache-Control'] = 'max-age=0'
    return response


@bp.route('/sleep/<count>')
def sleep(count):
    current_span = opentelemetry.trace.get_current_span()
    current_span.set_attribute('sleep', count)
    time.sleep(int(count))
    response = make_response(render_template('docker_debug.j2',
                                             colour=colour,
                                             environs=os.environ,
                                             headers=request.headers))
    response.headers['Cache-Control'] = 'max-age=0'
    return response


@bp.route('/size/<size>/<nchunks>')
def size(size, nchunks):
    chars = string.ascii_letters + string.digits + string.punctuation

    def generate():
        chunksize = int(size) // int(nchunks)
        for _ in range(int(nchunks)):
            yield "{}\n".format(''.join(random.choice(chars) for _ in range(chunksize - 1)))
        yield "{}\n".format(''.join(random.choice(chars) for _ in range((size % chunksize)-1)))
    current_span = opentelemetry.trace.get_current_span()
    current_span.set_attribute('size', size)
    return app.response_class(generate(), mimetype='text/plain')


@bp.route('/random/<code>/<percent>')
def random_code(code, percent):
    current_span = opentelemetry.trace.get_current_span()
    current_span.set_attribute('code', code)
    current_span.set_attribute('percent', percent)
    current_span.set_attribute('component', 'flask')
    if int(percent) >= random.randint(1, 100):
        result = ("Oh No!", int(code))
    else:
        result = ("Yay", 200)
    response = make_response(*result)
    return response


@bp.route('/ping')
def ping():
    response = make_response('pong')
    response.headers['Cache-Control'] = 'max-age=0'
    return response


@bp.route('/version')
def version_response():
    response = make_response(version)
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
    socketio.run(app, host='0.0.0.0', port=PORT, debug=DEBUG, allow_unsafe_werkzeug=True)
