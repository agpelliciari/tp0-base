MESSAGE="test message sended"

# Construir una imagen con netcat
docker build -t netcat-client -f- . <<EOF
FROM alpine:latest
RUN apk add --no-cache netcat-openbsd
CMD ["/bin/sh"]
EOF

NETWORK=$(docker inspect server --format='{{range .NetworkSettings.Networks}}{{.NetworkID}}{{end}}')
NETWORK_NAME=$(docker network inspect $NETWORK --format='{{.Name}}')

PORT=12345

RESULT=$(docker run --rm --network $NETWORK_NAME netcat-client sh -c "echo -n '$MESSAGE' | nc server $PORT")

if [ "$RESULT" == "$MESSAGE" ]; then
    echo "action: test_echo_server | result: success"
else
    echo "action: test_echo_server | result: fail"
fi

docker rmi netcat-client > /dev/null 2>&1