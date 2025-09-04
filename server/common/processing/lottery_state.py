import threading
from .. import utils

class LotteryState:
    def __init__(self, number_of_agencies):
        self.agencies_ready = set()
        self.waiting_clients = {} 
        self.lottery_done = False
        self.winners_by_agency = {}
        self.required_agencies = number_of_agencies

        self._lock = threading.RLock()

    def register_and_try_to_start_the_lottery(self, agency_id, client_sock, client_addr):
        """
        Registers a client that is waiting for lottery results and intents to start it
        
        Args:
            agency_id: Agency identifier
            client_sock: Client socket connection
            client_addr: Client address information
        """
        agency_id = str(agency_id)
        self.waiting_clients[agency_id] = (client_sock, client_addr)

        lottery_ready = False

        with self._lock:
            # register
            self.waiting_clients[agency_id] = (client_sock, client_addr)

            # marked as 'finalized'
            self.agencies_ready.add(agency_id)
            all_ready = len(self.agencies_ready) >= self.required_agencies

            # run the lottery
            if all_ready and not self.lottery_done:
                self._perform_lottery_locked()
                lottery_ready = True

        return lottery_ready

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

    def _perform_lottery_locked(self):
        """
        Performs the lottery draw if it hasn't been done yet.
        """        
        winners = {}
        
        for bet in utils.load_bets():
            if utils.has_won(bet):
                agency_id = str(bet.agency)
                if agency_id not in winners:
                    winners[agency_id] = []
                winners[agency_id].append(bet.document)
        
        self.winners_by_agency = winners
        self.lottery_done = True
    
    def get_winners_for_agency(self, agency_id):
        """
        Returns the list of winning documents for a specific agency.
        
        Args:
            agency_id: Agency identifier
            
        Returns:
            list: List of winning documents, or None if the lottery hasn't been performed yet
        """
        with self._lock:
            if not self.lottery_done:
                return None
            return list(self.winners_by_agency.get(str(agency_id), []))

    def copy_waiting_clients(self):
        with self._lock:
            return dict(self.waiting_clients)

    def clear_waiting_clients(self):
        with self._lock:
            self.waiting_clients.clear()

    def is_waiting(self, agency_id):
        with self._lock:
            return str(agency_id) in self.waiting_clients
