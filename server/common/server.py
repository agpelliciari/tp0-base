import socket
import logging
import signal
import threading

from . import utils
from .thread_queue import ThreadQueue
from .communication import Sender, Protocol, Receiver
from .processing import BatchProcessor, LotteryState
from .constants import *

class Server:
    def __init__(self, port, listen_backlog, number_of_clients):
        # Initialize server socket
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.bind(('', port))
        self._server_socket.listen(listen_backlog)
        
        self._running = True

        self._batch_processor = BatchProcessor()

        self._lottery_state = LotteryState(number_of_clients)

        self._process_batch_lock = threading.RLock()

        self._work_queue = ThreadQueue()
        self._worker_threads = []
        self._worker_count = number_of_clients
        
        for _ in range(self._worker_count):
            thread = threading.Thread(target=self._worker_thread, daemon=True)
            thread.start()
            self._worker_threads.append(thread)

        signal.signal(signal.SIGTERM, self._handle_sigterm)

    def _handle_sigterm(self, signum, frame):
        self._running = False
        try:
            self._server_socket.close()
        except Exception:
            pass

        for _ in range(self._worker_count):
            self._work_queue.put(None)


    def _worker_thread(self):
        """Process of every worker thread to handle the connection of the clients"""
        while self._running:
            client_sock = self._work_queue.get()
            
            if client_sock is None:
                self._work_queue.task_done()
                break

            try:
                self.__handle_client_connection(client_sock)
            except Exception as e:
                logging.exception(f"action: worker_thread | result: fail | error: {e}")
            finally:
                self._work_queue.task_done()

    def run(self):
        """
        Dummy Server loop

        Server that accept a new connections and establishes a
        communication with a client. After client with communucation
        finishes, servers starts to accept new connections again
        """

        self._server_socket.settimeout(TIMEOUT)
        try:
            while self._running:
                try:
                    client_sock = self.__accept_new_connection()
                    if client_sock:
                        self._work_queue.put(client_sock)
                except socket.timeout:
                    continue
                except Exception as e:
                    logging.error(f"action: accept_connections | result: fail | error: {e}")
                    break
            self._work_queue.join()
            
        finally:
                self._server_socket.close()

                for _ in range(self._worker_count):
                    self._work_queue.put(None)

                for thread in self._worker_threads:
                    thread.join()

                logging.info("action: close_server_socket | result: success")
                logging.info("action: graceful_shutdown | result: success")

    def __handle_client_connection(self, client_sock):
        """
        Read message from a specific client socket and closes the socket

        If a problem arises in the communication with the client, the
        client socket will also be closed
        """
        addr = None
        keep_open_for_waiting = False

        try:
            client_sock.settimeout(TIMEOUT)

            while self._running:
                try:
                    addr = client_sock.getpeername()

                    data = Receiver.receive_message(client_sock)
                    
                    if BATCH_KEY in data:                        
                        self._process_batch_request(client_sock, data)
                    
                    elif ACTION_KEY in data and data[ACTION_KEY] == BETTING_FINISHED_ACTION:
                        keep_open_for_waiting, lottery_done = self._handle_finish_action(client_sock, addr, data)

                        if lottery_done:
                            return
                        break

                except socket.timeout:
                    if not self._running:
                        break
                    continue
                    
                except ConnectionError as e:
                    logging.info(f"action: connection_closed | result: success | ip: {addr[IP_FIELD]} | message: {str(e)}")
                    break
                    
                except Exception as e:
                    break
                
        except Exception as e:
            logging.error(f"action: client_connection | result: fail | error: {e}")
        
        finally:
            if not keep_open_for_waiting:
                try:
                    if addr:
                        client_sock.close()
                        logging.info(f"action: close_client_socket | result: success | ip: {addr[IP_FIELD]}")
                except Exception:
                    try:
                        client_sock.close()
                    except Exception:
                        pass
                    logging.error("action: close_client_socket | result: error | message: Could not get peer name")

    def __accept_new_connection(self):
        """
        Accept new connections

        Function blocks until a connection to a client is made.
        Then connection created is printed and returned
        """

        try:
            # Connection arrived
            c, addr = self._server_socket.accept()
            logging.info(f'action: accept_connections | result: success | ip: {addr[IP_FIELD]}')
            return c
        except socket.timeout:
            return None

    def _notify_all_waiting_clients(self):
            """Notify all waiting clients with their respective winners"""
            waiting_clients_copy = self._lottery_state.copy_waiting_clients()

            for agency_id, (client_sock, addr) in waiting_clients_copy.items():
                try:
                    winners = self._lottery_state.get_winners_for_agency(agency_id)
                    winners_str = ",".join(winners) if winners else ""
                    
                    response = {
                        STATUS_KEY: STATUS_SUCCESS,
                        WINNERS_KEY: winners_str
                    }
                    
                    Sender.send_message(client_sock, response)
                    logging.info(f"action: notify_winners | result: success | agency_id: {agency_id} | winners: {len(winners)}")
                    
                except Exception as e:
                    logging.error(f"action: notify_winners | result: fail | agency_id: {agency_id} | error: {e}")
                finally:
                    try:
                        client_sock.close()
                        logging.info(f"action: close_client_socket | result: success | ip: {addr[IP_FIELD]}")
                    except Exception:
                        pass

            
            logging.info(f"action: notify_all_clients | result: success")

            logging.info("action: sorteo | result: success")
            
            self._lottery_state.clear_waiting_clients()

    def _process_batch_request(self, client_sock, data):
        batch_size, bets = Protocol.deserialize_batch_data(data)
        try:
            success, message, processed_bets = self._batch_processor.process_batch(batch_size, bets)

            if success and processed_bets:
                # store_bets is not thread-safe
                with self._process_batch_lock:
                    utils.store_bets(processed_bets)

                response = {
                    STATUS_KEY: STATUS_SUCCESS if success else STATUS_ERROR,
                    MESSAGE_KEY: message
                }

        except Exception as e:
            logging.error(f"action: process_batch | result: fail | error: {e}")
            response = {STATUS_KEY: STATUS_ERROR, MESSAGE_KEY: str(e)}

        Sender.send_message(client_sock, response)

    def _handle_finish_action(self, client_sock, addr, data):
        """
        Handles the wait of the clients before starting the lottery
        """
        agency_id = data.get(AGENCY_ID_KEY)

        lottery_ready = self._lottery_state.register_and_try_to_start_the_lottery(
            agency_id, client_sock, addr
        )
        if lottery_ready:
            threading.Thread(target=self._notify_all_waiting_clients, daemon=True).start()
            return True, True   
        
        return True, False