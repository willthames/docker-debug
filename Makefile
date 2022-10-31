VERSION:=$(shell git describe --long)

all: blue-push green-push

colours = blue green

$(colours):
	echo 'colour = "$@"' > colour.py
	docker build -t localhost:5000/docker-debug:$@ .

$(colours:%=%-push): %-push: %
	docker push localhost:5000/docker-debug:$<
	docker tag localhost:5000/docker-debug:$< localhost:5000/docker-debug:$<-${VERSION}
	docker push localhost:5000/docker-debug:$<-${VERSION}
