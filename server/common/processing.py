import logging
import random
from . import utils

class BatchProcessor:    
    def __init__(self):
        pass
    
    def process_batch(self, batch_size, bets_data):
        """
        Processes a complete batch of bets
        
        Args:
            batch_size: Number of bets in batch
            bets_data: List of dictionaries with bet data
            
        Returns:
            tuple: (success, message, processed bets)
        """
        try:            
            if not bets_data or len(bets_data) != batch_size:
                raise ValueError(f"Invalid batch: expected {batch_size} bets, got {len(bets_data)}")
            
            processed_bets = []
            
            for bet_data in bets_data:
                agency_id = str(random.randint(1, 5))
                
                bet = utils.Bet(
                    agency=agency_id,
                    first_name=bet_data.get('NOMBRE', ''),
                    last_name=bet_data.get('APELLIDO', ''),
                    document=bet_data.get('DOCUMENTO', ''),
                    birthdate=bet_data.get('NACIMIENTO', ''),
                    number=bet_data.get('NUMERO', '')
                )
                
                processed_bets.append(bet)
            
            utils.store_bets(processed_bets)
            
            logging.info(f"action: apuesta_recibida | result: success | cantidad: {batch_size}")
            
            return True, f"Batch de {batch_size} apuestas registrado correctamente", processed_bets
        
        except Exception as e:
            logging.error(f"action: apuesta_recibida | result: fail | cantidad: {batch_size} | error: {e}")
            return False, str(e), []