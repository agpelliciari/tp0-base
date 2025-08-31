import socket
import logging
import signal
import random
from . import utils
from . import communication

# Timeout in seconds for server socket operations
TIMEOUT = 1.0
IP = 0


class Server:
    def __init__(self, port, listen_backlog):
        # Initialize server socket
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.bind(('', port))
        self._server_socket.listen(listen_backlog)

        self._running = True

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
            addr = client_sock.getpeername()
            bet_data = communication.receive_message(client_sock)
            logging.info(f'action: receive_message | result: success | ip: {addr[IP]}')
            
            try:
                # the agency ID is assigned randomly
                agency_id = str(random.randint(1, 5))
                
                bet = utils.Bet(
                    agency=agency_id,
                    first_name=bet_data.get('NOMBRE', ''),
                    last_name=bet_data.get('APELLIDO', ''),
                    document=bet_data.get('DOCUMENTO', ''),
                    birthdate=bet_data.get('NACIMIENTO', ''),
                    number=bet_data.get('NUMERO', '')
                )
                
                utils.store_bets([bet])
                
                logging.info(f"action: apuesta_almacenada | result: success | dni: {bet.document} | numero: {bet.number}")
                
                response = {
                    'STATUS': 'SUCCESS',
                    'MESSAGE': 'Apuesta registrada correctamente'
                }
                communication.send_message(client_sock, response)
                
            except Exception as e:
                logging.error(f"action: process_bet | result: fail | error: {e}")
                response = {
                    'STATUS': 'ERROR',
                    'MESSAGE': str(e)
                }
                communication.send_message(client_sock, response)
                
        except Exception as e:
            logging.error(f"action: receive_message | result: fail | error: {e}")
        finally:
            addr = client_sock.getpeername()
            logging.info(f"action: close_client_socket | result: in_progress | ip: {addr[0]}")
            client_sock.close()
            logging.info(f"action: close_client_socket | result: success | ip: {addr[0]}")

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
