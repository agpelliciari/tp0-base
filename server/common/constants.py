# Constantes para la comunicación entre cliente y servidor

# Tamaño del encabezado que contiene la longitud del mensaje (4 bytes)
HEADER_SIZE = 4

# Separadores para el formato del mensaje
FIELD_SEPARATOR = '|'
KEY_VALUE_SEPARATOR = ':'
END_MARKER = '\n'

# Constantes para envío y recepción
ZERO_BYTES = 0
BUFFER_LIMIT = 4096

# Índices para acceder a pares clave-valor
KEY = 0
VALUE = 1

# Claves utilizadas en los mensajes
BATCH_KEY = 'BATCH_SIZE'
BET_PREFIX = 'BET_'
STATUS_KEY = 'STATUS'
STATUS_SUCCESS = 'SUCCESS'
STATUS_ERROR = 'ERROR'
MESSAGE_KEY = 'MESSAGE'
ACTION_KEY = 'ACTION'

# Constantes para manejo de bytes
BYTE_MASK = 0xFF

TIMEOUT = 1.0
IP = 0
STATUS = 'STATUS'
STATUS_SUCCESS = 'SUCCESS'
STATUS_ERROR = 'ERROR'
MESSAGE = 'MESSAGE'

BETTING_FINISHED_ACTION = 'FINISH_BETTING'
AGENCY_ID_KEY = 'AGENCY_ID'
                        

