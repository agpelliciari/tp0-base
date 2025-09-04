import logging
from . import utils

class LotteryState:
    """
    Manages the lottery state and tracks agencies that have finished
    sending their bets, as well as the winner processing.
    """
    def __init__(self, number_of_agencies):
        self.agencies_ready = set()
        self.waiting_clients = {} 
        self.lottery_done = False
        self.winners_by_agency = {}
        self.required_agencies = number_of_agencies

    def register_waiting_client(self, agency_id, client_sock, client_addr):
        """
        Registers a client that is waiting for lottery results
        
        Args:
            agency_id: Agency identifier
            client_sock: Client socket connection
            client_addr: Client address information
        """
        agency_id = str(agency_id)
        self.waiting_clients[agency_id] = (client_sock, client_addr)

    def agency_finished(self, agency_id):
        """
        Registers that an agency has finished sending bets.
        
        Args:
            agency_id: Agency identifier
            
        Returns:
            bool: True if all required agencies have finished, False otherwise
        """
        agency_id = str(agency_id)
        self.agencies_ready.add(agency_id)
        all_ready = len(self.agencies_ready) >= self.required_agencies
                
        return all_ready

    def perform_lottery(self):
        """
        Performs the lottery draw if it hasn't been done yet.
        
        Returns:
            bool: True if the lottery was performed now, False if it was already done
        """
        if self.lottery_done:
            logging.info("action: perform_lottery | result: already_done")
            return False
        
        winners = {}
        
        for bet in utils.load_bets():
            if utils.has_won(bet):
                agency_id = str(bet.agency)
                if agency_id not in winners:
                    winners[agency_id] = []
                winners[agency_id].append(bet.document)
        
        self.winners_by_agency = winners
        self.lottery_done = True
        
        return True

    def get_winners_for_agency(self, agency_id):
        """
        Returns the list of winning documents for a specific agency.
        
        Args:
            agency_id: Agency identifier
            
        Returns:
            list: List of winning documents, or None if the lottery hasn't been performed yet
        """
        if not self.lottery_done:
            logging.warning(f"action: get_winners | result: lottery_not_done | agency_id: {agency_id}")
            return None
        
        agency_id = str(agency_id)
        winners = self.winners_by_agency.get(agency_id, [])
                
        return winners

def create_lottery_manager(number_of_agencies):
    """
    Creates and returns a new instance of the lottery manager.
    
    Returns:
        LotteryState: Instance to manage the lottery state
    """
    return LotteryState(number_of_agencies)