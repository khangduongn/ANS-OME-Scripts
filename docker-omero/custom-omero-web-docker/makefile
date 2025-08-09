.PHONY: build

build:
	sudo docker build -t omero-web-customized .
	sudo docker compose -f ~/docker-omero/docker-compose.yml down
	sudo docker compose -f ~/docker-omero/docker-compose.yml up -d
	sudo docker ps

