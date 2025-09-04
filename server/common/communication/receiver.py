from ..constants import *
from .protocol import Protocol

import struct

class Receiver:
    @staticmethod
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
        
        return Protocol.deserialize_data(message_str)
    
    @staticmethod
    def receive_batch(sock):
        """
        Receives a complete batch.
        
        Args:
            sock: connected socket
            
        Returns:
            tuple: (batch_size, list of dictionary of bets)
        """
        data_dict = Receiver.receive_message(sock)
        
        return Protocol.deserialize_batch_data(data_dict)