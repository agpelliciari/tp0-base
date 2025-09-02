import socket
import logging
import signal
import random
from . import utils
from . import communication
from . import processing
from . import lottery_state

# Timeout in seconds for server socket operations
TIMEOUT = 1.0
IP = 0
STATUS = 'STATUS'
STATUS_SUCCESS = 'SUCCESS'
STATUS_ERROR = 'ERROR'
MESSAGE = 'MESSAGE'


class Server:
    def __init__(self, port, listen_backlog):
        # Initialize server socket
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.bind(('', port))
        self._server_socket.listen(listen_backlog)

        self._running = True

        self._batch_processor = processing.BatchProcessor()

        self._lottery_state = lottery_state.create_lottery_manager()

        signal.signal(signal.SIGTERM, self._handle_sigterm)

    def _handle_sigterm(self, signum, frame):
        """Handler for SIGTERM signal"""
        logging.info(f"action: graceful_shutdown | result: in_progress | message: SIGTERM received with num:{signum} and frame:{frame}")
        self._running = False

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
                    self.__handle_client_connection(client_sock)
            except socket.timeout:
                continue
            except Exception as e:
                logging.error(f"action: accept_connections | result: fail | error: {e}")
                break
        
        logging.info("action: close_server_socket | result: in_progress")
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
                    data = communication.receive_message(client_sock)
                    logging.info(f'action: receive_message | result: success | ip: {addr[IP]}')
                    
                    if 'BATCH_SIZE' in data:
                        batch_size, bets = communication.deserialize_batch_data(data)
                        
                        try:
                            success, message, processed_bets = self._batch_processor.process_batch(batch_size, bets)
                            
                            response = {
                                STATUS: STATUS_SUCCESS if success else STATUS_ERROR,
                                MESSAGE: message
                            }
                            communication.send_message(client_sock, response)
                            
                        except Exception as e:
                            logging.error(f"action: process_batch | result: fail | error: {e}")
                            response = {
                                STATUS: STATUS_ERROR,
                                MESSAGE: str(e)
                            }
                            communication.send_message(client_sock, response)
                    
                    elif 'ACTION' in data and data['ACTION'] == 'FINISH_BETTING':
                        agency_id = data.get('AGENCY_ID', agency_id or '0')
                        
                        self._lottery_state.register_waiting_client(agency_id, client_sock, addr)
                        logging.info(f"action: register_waiting_client | result: success | agency_id: {agency_id}")

                        all_ready = self._lottery_state.agency_finished(agency_id)

                        response = {
                            STATUS: STATUS_SUCCESS,
                            MESSAGE: "Apuestas recibidas correctamente"
                        }
                        communication.send_message(client_sock, response)
                        
                        if all_ready:
                            self._lottery_state.perform_lottery()
                            logging.info("action: sorteo | result: success")
                            self._notify_all_waiting_clients()
                            return
                        break

                except socket.timeout:
                    if not self._running:
                        break
                    continue
                    
                except ConnectionError as e:
                    logging.info(f"action: connection_closed | result: success | ip: {addr[IP]} | message: {str(e)}")
                    break
                    
                except Exception as e:
                    break
                
        except Exception as e:
            logging.error(f"action: client_connection | result: fail | error: {e}")
        
        if agency_id not in self._lottery_state.waiting_clients:
            try:
                if addr:
                    logging.info(f"action: close_client_socket | result: in_progress | ip: {addr[0]}")
                client_sock.close()
                if addr:
                    logging.info(f"action: close_client_socket | result: success | ip: {addr[0]}")
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
            logging.info('action: accept_connections | result: in_progress')
            c, addr = self._server_socket.accept()
            logging.info(f'action: accept_connections | result: success | ip: {addr[0]}')
            return c
        except socket.timeout:
            return None

    def _notify_all_waiting_clients(self):
            """Notify all waiting clients with their respective winners"""
            for agency_id, (client_sock, addr) in list(self._lottery_state.waiting_clients.items()):
                try:
                    winners = self._lottery_state.get_winners_for_agency(agency_id)
                    winners_str = ",".join(winners) if winners else ""
                    
                    response = {
                        STATUS: STATUS_SUCCESS,
                        "WINNERS": winners_str
                    }
                    
                    communication.send_message(client_sock, response)
                    logging.info(f"action: notify_winners | result: success | agency_id: {agency_id} | winners: {len(winners)}")
                    
                except Exception as e:
                    logging.error(f"action: notify_winners | result: fail | agency_id: {agency_id} | error: {e}")
                finally:
                    try:
                        client_sock.close()
                        logging.info(f"action: close_client_socket | result: success | ip: {addr[IP]}")
                    except:
                        pass
            
            logging.info(f"action: notify_all_clients | result: success")
            self._lottery_state.waiting_clients.clear()