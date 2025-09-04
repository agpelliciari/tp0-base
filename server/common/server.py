import socket
import logging
import signal
import threading
import queue
from .communication import Sender 
from .communication import Protocol
from .communication import Receiver
from .constants import *
from . import processing
from . import lottery_state

class Server:
    def __init__(self, port, listen_backlog, number_of_clients):
        # Initialize server socket
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.bind(('', port))
        self._server_socket.listen(listen_backlog)
        
        self._running = True

        self._batch_processor = processing.BatchProcessor()

        self._lottery_state = lottery_state.create_lottery_manager(number_of_clients)

        self._lottery_lock = threading.RLock()
        self._work_queue = queue.Queue()
        self._worker_threads = []
        
        for i in range(number_of_clients):
            thread = threading.Thread(target=self._worker_thread, daemon=True)
            thread.start()
            self._worker_threads.append(thread)

        signal.signal(signal.SIGTERM, self._handle_sigterm)

    def _handle_sigterm(self, signum, frame):
        """Handler for SIGTERM signal"""
        logging.info(f"action: graceful_shutdown | result: in_progress | message: SIGTERM received with num:{signum} and frame:{frame}")
        self._running = False

    def _worker_thread(self):
        """Process of every worker thread to handle the connection of the clients"""
        while self._running:
            try:
                client_sock = self._work_queue.get()
                self.__handle_client_connection(client_sock)
                self._work_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                logging.error(f"action: worker_thread | result: fail | error: {e}")

    def run(self):
        """
        Dummy Server loop

        Server that accept a new connections and establishes a
        communication with a client. After client with communucation
        finishes, servers starts to accept new connections again
        """

        self._server_socket.settimeout(TIMEOUT)
        
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
        self._server_socket.close()
        logging.info("action: close_server_socket | result: success")
        logging.info("action: graceful_shutdown | result: success")

    def __handle_client_connection(self, client_sock):
        """
        Read message from a specific client socket and closes the socket

        If a problem arises in the communication with the client, the
        client socket will also be closed
        """
        try:
            client_sock.settimeout(TIMEOUT)
            addr = None
            agency_id = None

            while self._running:
                try:
                    addr = client_sock.getpeername()
                    data = Receiver.receive_message(client_sock)
                    
                    if BATCH_KEY in data:
                        batch_size, bets = Protocol.deserialize_batch_data(data)
                        
                        try:
                            with self._lottery_lock:
                                success, message, processed_bets = self._batch_processor.process_batch(batch_size, bets)
                            
                            response = {
                                STATUS_KEY: STATUS_SUCCESS if success else STATUS_ERROR,
                                MESSAGE_KEY: message
                            }
                            Sender.send_message(client_sock, response)
                            
                        except Exception as e:
                            logging.error(f"action: process_batch | result: fail | error: {e}")
                            response = {
                                STATUS_KEY: STATUS_ERROR,
                                MESSAGE_KEY: str(e)
                            }
                            Sender.send_message(client_sock, response)
                    
                    elif ACTION_KEY in data and data[ACTION_KEY] == BETTING_FINISHED_ACTION:
                        agency_id = data.get(AGENCY_ID_KEY)
                        
                        with self._lottery_lock:
                            self._lottery_state.register_waiting_client(agency_id, client_sock, addr)

                        lottery_ready = self._lottery_state.agency_finished(agency_id)
                        
                        if lottery_ready:
                            self._lottery_state.perform_lottery()
                            logging.info("action: sorteo | result: success")
                            threading.Thread(target=self._notify_all_waiting_clients).start()
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
        
        with self._lottery_lock:
            if agency_id not in self._lottery_state.waiting_clients:
                try:
                    if addr:
                        logging.info(f"action: close_client_socket | result: in_progress | ip: {addr[IP_FIELD]}")
                    client_sock.close()
                    if addr:
                        logging.info(f"action: close_client_socket | result: success | ip: {addr[IP_FIELD]}")
                except:
                    client_sock.close()
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
            with self._lottery_lock:
                waiting_clients_copy = dict(self._lottery_state.waiting_clients)

            for agency_id, (client_sock, addr) in waiting_clients_copy.items():
                try:
                    with self._lottery_lock:
                        winners = self._lottery_state.get_winners_for_agency(agency_id)

                    winners_str = ",".join(winners) if winners else ""
                    
                    response = {
                        STATUS_KEY: STATUS_SUCCESS,
                        "WINNERS": winners_str
                    }
                    
                    Sender.send_message(client_sock, response)
                    logging.info(f"action: notify_winners | result: success | agency_id: {agency_id} | winners: {len(winners)}")
                    
                except Exception as e:
                    logging.error(f"action: notify_winners | result: fail | agency_id: {agency_id} | error: {e}")
                finally:
                    try:
                        client_sock.close()
                        logging.info(f"action: close_client_socket | result: success | ip: {addr[IP_FIELD]}")
                    except:
                        pass
            
            logging.info(f"action: notify_all_clients | result: success")
            
            with self._lottery_lock:
                self._lottery_state.waiting_clients.clear()