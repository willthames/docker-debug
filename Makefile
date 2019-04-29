VERSION:=$(shell git describe --long)

all: blue-push green-push

colours = blue green

$(colours):
	echo 'colour = "$@"' > colour.py
	docker build -t willthames/docker-debug:$@ .

$(colours:%=%-push): %-push: %
	docker push willthames/docker-debug:$<
	docker tag willthames/docker-debug:$< willthames/docker-debug:$<-${VERSION}
	docker push willthames/docker-debug:$<-${VERSION}
