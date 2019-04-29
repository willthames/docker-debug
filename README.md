# Build

Run `make $colour` to create a container labelled with that colour that shows a header in that colour.

Note that the foreground colour is white, so light container names are likely a bad idea

# Run

`docker run -e ROOT_CONTEXT=/docker-debug -p 5000:5000 willthames/docker-debug`

will create a docker-debug service responding to http://localhost:5000/docker-debug

The `ROOT_CONTEXT` is optional, if omitted it will respond to http://localhost:5000/

# Websockets

The websocket code has been heavily based on https://github.com/miguelgrinberg/Flask-SocketIO,
included under the MIT License.

Connect to http://localhost:5000/docker-debug/ws to see websocket demo

To get more debug information, particularly for websockets, set the `DEBUG` environment
variable to `True`. You can also set `localStorage.debug = '*'` in your web console
in your browser.
