all: blue-push green-push

blue green:
	echo 'colour = "$@"' > colour.py
	docker build -t willthames/docker-debug:$@ .

blue-push: blue
	docker push willthames/docker-debug:$<
green-push: green
	docker push willthames/docker-debug:$<
