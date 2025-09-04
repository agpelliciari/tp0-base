from ..constants import *

class Protocol:
    @staticmethod
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
            fields.append(f"{key}{KEY_VALUE_SEPARATOR}{value}")
        
        return FIELD_SEPARATOR.join(fields) + END_MARKER

    @staticmethod
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
        
        result[BATCH_KEY] = str(batch_size)
        
        for i, bet in enumerate(bets, 1):
            bet_str = Protocol.serialize_data(bet).rstrip(END_MARKER)
            result[f'BET_{i}'] = bet_str
        
        return Protocol.serialize_data(result)

    @staticmethod
    def deserialize_data(data_str):
        """
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

    @staticmethod
    def deserialize_batch_data(data_dict):
        """
        Deserializes a dictionary with the batch of bets.
        
        Args:
            data_dict: dictionary with the batch of bets
            
        Returns:
            tuple: (batch_size, list of dictionary of bets)
        """
        if BATCH_KEY not in data_dict:
            return 0, []
        
        try:
            batch_size = int(data_dict[BATCH_KEY])
        except ValueError:
            return 0, []
        
        bets = []
        
        for i in range(1, batch_size + 1):
            bet_key = f'BET_{i}'
            if bet_key in data_dict:
                bet_str = data_dict[bet_key] + END_MARKER
                bet_data = Protocol.deserialize_data(bet_str)
                bets.append(bet_data)
        
        return batch_size, bets
    
    @staticmethod
    def decode_string(sequence_of_bytes):
        """
        Decodes a secuence of bytes into an string
        """   
        return sequence_of_bytes.decode()
    
    @staticmethod
    def encode_string(string_to_convert):
        """
        Encodes an string into a secuence of bytes
        """   
        return string_to_convert.encode()
    
    @staticmethod
    def bytes_to_int(bytes_data):
        """
        Converts bytes into an int using Big Endian
        """          
        result = 0
        for byte in bytes_data:
            result = (result << 8) + byte
        
        return result
    
    @staticmethod
    def int_to_bytes(value, size=HEADER_SIZE):
        """
        Converts an int into bytes using Big Endian
        """ 
        result = bytearray(size)
        
        for i in range(size - 1, -1, -1):
            result[size - 1 - i] = (value >> (i * 8)) & BYTE_MASK
        
        return bytes(result)
