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
    networks:
      - testing_net
    volumes:
      - ./server/config.ini:/config.ini
EOF

for i in $(seq 1 "$CANTIDAD"); do
cat >> "$SALIDA" <<EOF

  client$i:
    container_name: client$i
    image: client:latest
    entrypoint: /client
    environment:
      - CLI_ID=$i
      - NOMBRE=Apostador$i
      - APELLIDO=Apellido$i
      - DOCUMENTO=3090446$i
      - NACIMIENTO=1999-03-1$i
      - NUMERO=757$i
    networks:
      - testing_net
    depends_on:
      - server
    volumes:
      - ./client/config.yaml:/config.yaml
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
