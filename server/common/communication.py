import socket
import struct

HEADER_SIZE = 4
FIELD_SEPARATOR = '|'
KEY_VALUE_SEPARATOR = ':'
END_MARKER = '\n'
ZERO_BYTES = 0
BUFFER_LIMIT = 4096
KEY = 0
VALUE = 1


def serialize_data(data_dict):
    """
    Serializes a dictionary into a string with defined and separated fields.
    
    Args:
        data_dict: dictionary with data to serialize
        
    Returns:
        string: key1:value1|key2:value2|...
    """
    fields = []
    for key, value in data_dict.items():
        escaped_value = str(value).replace(FIELD_SEPARATOR, '\\' + FIELD_SEPARATOR)
        escaped_value = escaped_value.replace(KEY_VALUE_SEPARATOR, '\\' + KEY_VALUE_SEPARATOR)
        fields.append(f"{key}{KEY_VALUE_SEPARATOR}{escaped_value}")
    
    return FIELD_SEPARATOR.join(fields) + END_MARKER

def serialize_batch_data(batch_size, bets):
    """
    Serializes a batch of bets.
    
    Args:
        batch_size: number of bets in the batch
        bets: dictionary containing the data from the bets
        
    Returns:
        string: BATCH_SIZE:3|BET_1:datos_apuesta1|BET_2:datos_apuesta2|...
    """
    result = {}
    
    result['BATCH_SIZE'] = str(batch_size)
    
    for i, bet in enumerate(bets, 1):
        bet_str = serialize_data(bet).rstrip(END_MARKER)
        result[f'BET_{i}'] = bet_str
    
    return serialize_data(result)



def deserialize_data(data_str):
    """
    Deserializa un string en formato separado a un diccionario.
    Deserializes a string into a data dictionary
    
    Args:
        data_str: serialized string
        
    Returns:
        dictionary with the deserialized data
    """
    result = {}
    
    if data_str.endswith(END_MARKER):
        data_str = data_str[:-len(END_MARKER)]
    
    fields = []
    escape = False
    current_field = ""
    
    for char in data_str:
        if escape:
            current_field += char
            escape = False
        elif char == '\\':
            escape = True
        elif char == FIELD_SEPARATOR:
            fields.append(current_field)
            current_field = ""
        else:
            current_field += char
    
    if current_field:
        fields.append(current_field)
    
    for field in fields:
        if KEY_VALUE_SEPARATOR in field:
            parts = field.split(KEY_VALUE_SEPARATOR, VALUE)
            result[parts[KEY]] = parts[VALUE]
    
    return result

def deserialize_batch_data(data_dict):
    """
    Deserializes a dictionary with the batch of bets.
    
    Args:
        data_dict: dictionary with the batch of bets
        
    Returns:
        tuple: (batch_size, list of dictionary of bets)
    """
    if 'BATCH_SIZE' not in data_dict:
        return 0, []
    
    try:
        batch_size = int(data_dict['BATCH_SIZE'])
    except ValueError:
        return 0, []
    
    bets = []
    
    for i in range(1, batch_size + 1):
        bet_key = f'BET_{i}'
        if bet_key in data_dict:
            bet_str = data_dict[bet_key] + END_MARKER
            bet_data = deserialize_data(bet_str)
            bets.append(bet_data)
    
    return batch_size, bets

def send_message(sock, data_dict):
    """
    Sends a serialized message through the socket.
    Uses a length prefix to avoid short writes
    
    Args:
        sock: the connected socket
        data_dict: a data dictionary
        
    Raises:
        RuntimeError: error in the connection
    """
    message = serialize_data(data_dict)
    message_bytes = message.encode()
    
    length_prefix = struct.pack('!I', len(message_bytes))
    
    # send length prefix
    total_sent = ZERO_BYTES
    while total_sent < HEADER_SIZE:
        sent_data = sock.send(length_prefix[total_sent:])
        if sent_data == ZERO_BYTES:
            raise RuntimeError("Socket connection broken")
        total_sent += sent_data
    
    # send payload
    total_sent = ZERO_BYTES
    while total_sent < len(message_bytes):
        sent_data = sock.send(message_bytes[total_sent:])
        if sent_data == ZERO_BYTES:
            raise RuntimeError("Socket connection broken")
        total_sent += sent_data


def receive_message(sock):
    """
    Receives the complete message from the socket.
    Uses a length prefix to avoid short reads.
    
    
    Args:
        sock: the connected socket
        
    Returns:
        a dictionary containing the received data
        
    Raises:
        RuntimeError: error in the connection
    """
    length_bytes = b''
    while len(length_bytes) < HEADER_SIZE:
        received_data = sock.recv(HEADER_SIZE - len(length_bytes))
        if not received_data:
            raise RuntimeError("Connection closed before receiving complete header")
        length_bytes += received_data
    
    message_length = struct.unpack('!I', length_bytes)[0]
    
    message_bytes = b''
    while len(message_bytes) < message_length:
        received_data = sock.recv(min(BUFFER_LIMIT, message_length - len(message_bytes)))
        if not received_data:
            raise RuntimeError("Connection closed before receiving complete message")
        message_bytes += received_data
    
    message_str = message_bytes.decode('utf-8')

    return deserialize_data(message_str)

def receive_batch_message(sock):
    """
    Receives a complete batch.
    
    Args:
        sock: connected socket
        
    Returns:
        tuple: (batch_size, list of dictionary of bets)
    """
    data_dict = receive_message(sock)
    
    return deserialize_batch_data(data_dict)