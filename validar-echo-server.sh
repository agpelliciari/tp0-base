#!/bin/sh

MESSAGE="test message sended"

NAME="server"
PORT=12345

docker build -t netcat-client -f- . <<EOF
FROM alpine:latest
RUN apk add --no-cache netcat-openbsd
CMD ["/bin/sh"]
EOF

NETWORK=$(docker inspect server --format='{{range .NetworkSettings.Networks}}{{.NetworkID}}{{end}}')
NETWORK_NAME=$(docker network inspect $NETWORK --format='{{.Name}}')

RESULT=$(docker run --rm --network $NETWORK_NAME netcat-client sh -c "echo '$MESSAGE' | nc -w 1 $NAME $PORT")

if [ "$RESULT" = "$MESSAGE" ]; then
    echo "action: test_echo_server | result: success"
    exit 0
else
    echo "action: test_echo_server | result: fail"
    exit 1
fi

