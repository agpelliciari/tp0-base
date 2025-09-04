import logging
import random
from .. import utils

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
        if not bets_data or len(bets_data) != batch_size:
            msg = f"Invalid batch: expected {batch_size} bets, got {len(bets_data) if bets_data else 0}"
            logging.warning(f"action: process_batch | result: invalid | reason: {msg}")
            return False, msg, []
            
        processed_bets = []
        
        for bet_data in bets_data:
            agency_id = bet_data.get('AGENCY_ID')
            
            bet = utils.Bet(
                agency=agency_id,
                first_name=bet_data.get('NOMBRE', ''),
                last_name=bet_data.get('APELLIDO', ''),
                document=bet_data.get('DOCUMENTO', ''),
                birthdate=bet_data.get('NACIMIENTO', ''),
                number=bet_data.get('NUMERO', '')
            )
            
            processed_bets.append(bet)
            
        
        msg = f"Batch de {batch_size} apuestas procesado"

        logging.info(f"action: process_batch | result: success | cantidad: {batch_size}")

        return True, msg, processed_bets