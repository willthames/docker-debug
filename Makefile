all: blue-push green-push

blue green:
	echo 'colour = "$@"' > colour.py
	docker build -t willthames/docker-debug:$@ .

blue-push: blue
green-push: green
	docker push willthames/docker-debug:$@
