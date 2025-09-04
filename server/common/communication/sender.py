from ..constants import *
from .protocol import Protocol

import struct

class Sender:
    @staticmethod    
    def send_message(sock, data_dict):
        """"
        Sends a serialized message through the socket.
        Uses a length prefix to avoid short writes
        
        Args:
            sock: the connected socket
            data_dict: a data dictionary
            
        Raises:
            RuntimeError: error in the connection
        """
        message = Protocol.serialize_data(data_dict)

        message_bytes = Protocol.encode_text(message)
    
        length_prefix = Protocol.uint_to_bytes(len(message_bytes))
        
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
