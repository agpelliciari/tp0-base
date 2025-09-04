# Arquitectura general

## Separacion de responsabilidades
Al servidor y al cliente se le pueden distinguir las siguientes capas:
- **Capa de logica de negocio**: maneja el flujo de cada una de las entidades y sus interacciones.
- **Capa de comunicacion**: maneja la serializacion, deserializacion y el envio
- **Capa de procesamiento**: maneja la logica de procesamiento de apuestas.

El servidor, en comparacion con el cliente, se puede observar que quedo mas acoplado con objetos particulares de las distintas capas. Preferi priorizar este enfoque ya que es la entidad padre y la que maneja la logica mas compleja.

## Concurrencia

El hilo principal del servidor hace accept() y encola cada socket de los clientes aceptados en una cola de trabajo (`ThreadQueue`).

Un pool de threads hace `get()` sobre la cola y atiende cada conexión con `__handle_client_connection`.

Esta cola permite manejar múltiples clientes en paralelo.

En el shutdown se joinea a cada uno de estos threads para asi cerrar ordenadamente todos los recursos.

Utilice threading para manejar concurrencia en python ya que la aplicacion no requiere operaciones intensivas, de alto computo o de alta demanda de la CPU. 

En caso contrario, threads en python no seria la mejor opcion para resolver un problema de concurrencia por el GIL. Este global interpreter lock funciona como un mutex que permite que solo un hilo ejecute en el interprete de python a la vez, dejando bloqueados a los demas hilos. Pero como mencione antes, en este caso no es un problema ya que la aplicacion no requiere operaciones intensivas de CPU.

# Mecanismos de sincronización

## Proteccion de secciones criticas con RLock
Para garantizar sincronizacion en las secciones criticas, se utilizo `RLock` de la libreria threading.

Un `RLock` es un tipo de bloqueo que permite que el mismo hilo adquiera el bloqueo multiple veces sin causar un deadlock. Esto es util en situaciones donde una funcion puede llamar a otra funcion que tambien necesita adquirir el mismo bloqueo.

Algunas de las secciones criticas que se protegieron con `RLock` son:

### Almacenamiento de apuestas en el servidor
En esta seccion múltiples workers luego de terminar el procesamiento van a intentar acceder a este metodo de registro de apuestas en paralelo y este no es thread-safe.

Lo resolvi aplicando en el servidor lo siguiente:

```
with self._process_batch_lock:
    utils.store_bets(processed_bets)
```
una vez que un worker termina de procesar un batch, adquiere el lock y persiste las apuestas en el repositorio.

### Estado de la loteria
Para esto implemente una clase `LotteryState` que encapsula el estado de la loteria y provee metodos thread-safe para interactuar con cada una de las agencias.

Esta clase funciona de la siguiente manera:

Posee un lock interno (`RLock`) y operación atómica:
```
register_and_try_to_start_the_lottery(agency_id, sock, addr):
```
en esta funcion se:
1. registra al cliente en waiting_clients almacenando sus datos del socket (ip, puerto)
2. se marca la agencia en agencies_ready
3. si se completan en caso de que hayan terminado todas las agencias se ejecuta el sorteo
   1. el servidor comienza a notificar los ganadores
4. caso contrario, se queda en espera.
   1. no cierra el socket (queda en espera hasta ser notificado).

# Graceful Shutdown
Para garantizar un cierre ordenado del servidor liberando los recursos, el servidor implementa un mecanismo de cierre ordenado.

Este se dara en caso de que haya una interrupcion, un error en el servidor o cliente y cuando un cliente termine su flujo de trabajo.

Algunos de los recursos que se liberan son:
- FD del socket del servidor

- FDs de sockets de cliente
  - Los que no quedan en espera: close() en el finally del handler.
  - Los que sí quedan en espera: close() en el notificador al terminar de enviar ganadores.

- Pool de threads: join().

- Ítems de la ThreadQueue:
  - task_done() por cada socket
  - join() asegura que no queden tareas sin marcar.

- Estructuras del estado:

  - waiting_clients: clear_waiting_clients() en el notificador (luego de cerrar sockets).

# Comunicacion

## Paquetes
Cada uno de los mensajes a partir de los cuales se comunican cliente y servidor se empaquetan de la siguiente manera:

```
[largo del mensaje] [payload]
```

### Largo del mensaje
Este "header" es un bloque fijo, siempre del mismo tamaño, que indica cuántos bytes hay que leer para obtener el payload completo.

### Payload
El payload es el contenido del mensaje, que puede ser de tamaño variable.

Aplica un estilo de formato tipo "clave:valor" para facilitar el parseo y la extensibilidad del protocolo.

Para delimitar y diferenciar cada par clave-valor, se utilizan un separador de campos '|' y un señalizador de fin de mensaje '\n'.

### Ejemplo de paquete
Mensaje generico
```
ACTION:BETTING_FINISHED|AGENCY_ID:3\n
```
Mensaje de Batch
``` 
BATCH_SIZE:2|BET_1:NOMBRE:Ana\|Maria:APELLIDO:Perez:...|BET_2:... \n
```

## Serializacion y deserializacion

### Cliente
- ```serializeData```: construye key:value|key:value|... + \n, escapando | y : en valores.

- ```serializeBatchData```: compone BATCH_SIZE:n|BET_1:...|BET_2:... + \n, asegurando orden de campos relevantes dentro de cada bet (NOMBRE, APELLIDO, DOCUMENTO, NACIMIENTO, NUMERO, AGENCY_ID).

- ```deserializeData```: recorre caracter a caracter, respetando escapes y separando por |, luego divide cada campo por el primer :.

### Servidor
Misma logica que en el cliente pero se implemento una clase `Protocol`en la cual se encapsula toda la logica de serializacion y deserializacion.

- ```Protocol.serialize_data()``` / ```Protocol.deserialize_data()```:

- ```Protocol.serialize_batch_data()``` / ```Protocol.deserialize_batch_data()```

## Envio y recepcion de mensajes
Para el envio y recepcion de mensajes se implemento la interfaz de sockets. Esta interfaz se encuentra en el medio de las capas de comunicacion y logica de negocio.

### Solucion a short-write
En el **cliente** se utiliza el metodo `writeExactBytes` dentro de un bucle que verifica la condicion `totalSent == len(data)`.

En el **servidor** se utiliza el metodo `send` el cual tambien se encapsula en un bucle condicional el cual valida un limite a partir del header de largo del mensaje.

### Solucion a short-read
En el **cliente** se utiliza el metodo `readExactBytes` dentro de un bucle que acumula bytes hasta llegar al largo del paquete obtenido en la cabecera.

En el **servidor** se utiliza el metodo `recv` y realiza una logica similar a la del cliente, acumulando bytes hasta llegar al largo del paquete.