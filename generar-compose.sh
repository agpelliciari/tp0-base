#!/usr/bin/env bash

SALIDA="$1"
CANTIDAD="$2"

cat > "$SALIDA" <<EOF
name: tp0
services:
  server:
    container_name: server
    image: server:latest
    entrypoint: python3 /main.py
    environment:
      - PYTHONUNBUFFERED=1
      - LOGGING_LEVEL=DEBUG
    networks:
      - testing_net
EOF

for i in $(seq 1 "$CANTIDAD"); do
cat >> "$SALIDA" <<EOF

  client$i:
    container_name: client$i
    image: client:latest
    entrypoint: /client
    environment:
      - CLI_ID=$i
      - CLI_LOG_LEVEL=DEBUG
    networks:
      - testing_net
    depends_on:
      - server
EOF
done

cat >> "$SALIDA" <<EOF

networks:
  testing_net:
    ipam:
      driver: default
      config:
        - subnet: 172.25.125.0/24
EOF

echo "Compose generado en $SALIDA"
