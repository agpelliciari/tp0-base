package common

import (
	"context"
	"io"
	"net"
	"os/signal"
	"syscall"
	"time"

	"github.com/op/go-logging"
)

const (
    STATUS_SUCCESS = "SUCCESS"
    STATUS_ERROR   = "ERROR"
    MESSAGE_KEY    = "MESSAGE"
    STATUS_KEY     = "STATUS"
)

var log = logging.MustGetLogger("log")

// ClientConfig Configuration used by the client
type ClientConfig struct {
	ID            string
	ServerAddress string
	LoopAmount    int
	LoopPeriod    time.Duration
    BatchMaxAmount int


}

// Client Entity that encapsulates how
type Client struct {
	config ClientConfig
	conn   net.Conn
    batchProcessor *BatchProcessor

}

// NewClient Initializes a new client receiving the configuration
// as a parameter
func NewClient(config ClientConfig) *Client {
	client := &Client{
		config: config,
        batchProcessor: NewBatchProcessor(config.ID, config.BatchMaxAmount),
	}
	return client
}

// CreateClientSocket Initializes client socket. In case of
// failure, error is printed in stdout/stderr and exit 1
// is returned
func (c *Client) createClientSocket() error {
	conn, err := net.Dial("tcp", c.config.ServerAddress)
	if err != nil {
		log.Criticalf(
			"action: connect | result: fail | client_id: %v | error: %v",
			c.config.ID,
			err,
		)
	}
	c.conn = conn
	return nil
}

// Close the actual connection with log messages
func (c *Client) closeConnection() {
    if c.conn == nil {
        log.Warningf("action: close_connection | result: skip | client_id: %v | error: connection is nil", c.config.ID)
        return
    }

    log.Infof("action: close_connection | result: in_progress | client_id: %v", c.config.ID)
    c.conn.Close()
    c.conn = nil
    log.Infof("action: close_connection | result: success | client_id: %v", c.config.ID)
}

// checks if a SIGTERM was received
func (c *Client) checkTerminationSignal(ctx context.Context) bool {
    select {
    case <-ctx.Done():
        log.Infof("action: graceful_shutdown | result: in_progress | client_id: %v | message: SIGTERM received", c.config.ID)
        return true
    default:
        return false
    }
}

// validates that the connection is still active
func (c *Client) connectionIsActive() bool {
    if c.conn != nil {
        return true
    }
    
    log.Warningf("action: send_batch | result: retry | client_id: %v | error: connection not established", c.config.ID)
    if err := c.createClientSocket(); err != nil {
        return false
    }
    return true
}

// encapsulates the communication with the server
func (c *Client) sendAndProcessBatch(batch []BetData, batchIndex int) bool {
    err := c.batchProcessor.SendBatch(c.conn, batch)
    if err != nil {
        log.Errorf("action: send_batch | result: fail | client_id: %v | batch_size: %d | error: %v",
            c.config.ID, len(batch), err)
        c.conn = nil
        return false
    }
    
    response, err := ReceiveMessage(c.conn)
    if err != nil {
        log.Errorf("action: receive_response | result: fail | client_id: %v | error: %v",
            c.config.ID, err)
        c.conn = nil
        return false
    }
    
    c.processBatchResponse(response, batch, batchIndex)
    return true
}

// processes the answer from the server
func (c *Client) processBatchResponse(response map[string]string, batch []BetData, batchIndex int) {
    if response[STATUS_KEY] == STATUS_SUCCESS {
        log.Infof("action: apuesta_enviada | result: success | batch_size: %d | batch_number: %d",
            len(batch), batchIndex+1)
    } else {
        log.Errorf("action: apuesta_enviada | result: fail | batch_size: %d | error: %s",
            len(batch), response[MESSAGE_KEY])
    }
}

// waits before sending the next batch of bets, checks if a SIGTERM was received
func (c *Client) waitForNextBatch(ctx context.Context) bool {
    select {
    case <-ctx.Done():
        return true
    case <-time.After(c.config.LoopPeriod):
        return false
    }
}

// StartClientLoop Send messages to the client until some time threshold is met
func (c *Client) StartClientLoop() {
    ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGTERM)
    defer stop()
    
    // persistent connection
    if err := c.createClientSocket(); err != nil {
        log.Criticalf("action: connect | result: fail | client_id: %v | error: %v", c.config.ID, err)
        return
    }
    defer c.closeConnection()

    reader, file, err := c.batchProcessor.OpenCSVReader()
    if err != nil {
        log.Criticalf("action: open_csv | result: fail | client_id: %v | error: %v", c.config.ID, err)
        return
    }
    defer file.Close()

    batchIndex := 0
    for {
        if c.checkTerminationSignal(ctx) {
            return
        }

        if !c.connectionIsActive() {
            continue
        }
        
        currentBatch, err := c.batchProcessor.ReadNextBatch(reader)
        if err == io.EOF {
            log.Infof("action: read_batch | result: success | client_id: %v | message: No more batches", c.config.ID)
            break
        }
        if err != nil {
            log.Errorf("action: read_batch | result: fail | client_id: %v | error: %v", c.config.ID, err)
            continue
        }
        
        if !c.sendAndProcessBatch(currentBatch, batchIndex) {
            continue
        }
        
        batchIndex++
        
        if c.waitForNextBatch(ctx) {
            return
        }
    }

    log.Infof("action: loop_finished | result: success | client_id: %v | batches_sent: %d", 
        c.config.ID, batchIndex)
}
