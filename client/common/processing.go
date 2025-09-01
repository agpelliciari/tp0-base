package common

import (
	"encoding/csv"
	"fmt"
	"io"
	"net"
	"os"
	"path/filepath"
)

const (
    NAME = 0
    SURNAME = 1
    DOCUMENT_NUMBER = 2
	BIRTH_DATE = 3
	NUMBER = 4
	RECORD_MAX_SIZE = 5
)

// data from a bet
type BetData struct {
    Nombre     string
    Apellido   string
    Documento  string
    Nacimiento string
    Numero     string
}

// handles the processing
type BatchProcessor struct {
    clientID      string
    batchMaxSize  int
}

// creates a batch
func NewBatchProcessor(clientID string, batchMaxSize int) *BatchProcessor {
    return &BatchProcessor{
        clientID:      clientID,
        batchMaxSize:  batchMaxSize,
    }
}

func createBetDataFromRecord(record []string) BetData {
    return BetData{
        Nombre:     record[NAME],
        Apellido:   record[SURNAME],
        Documento:  record[DOCUMENT_NUMBER],
        Nacimiento: record[BIRTH_DATE],
        Numero:     record[NUMBER],
    }
}

// opens the file and returns a Reader for the processing
func (bp *BatchProcessor) OpenCSVReader() (*csv.Reader, *os.File, error) {
    filePath := filepath.Join(".data", fmt.Sprintf("agency-%s.csv", bp.clientID))

    if _, err := os.Stat(filePath); os.IsNotExist(err) {
        return nil, nil, fmt.Errorf("CSV file not found for client %s: %v", bp.clientID, err)
    }
    
    file, err := os.Open(filePath)
    if err != nil {
        return nil, nil, fmt.Errorf("error opening CSV file: %v", err)
    }

    reader := csv.NewReader(file)
    reader.Comma = ','
    
    return reader, file, nil
}

// reads only the necessary registers for the processing of a batch
func (bp *BatchProcessor) ReadNextBatch(reader *csv.Reader) ([]BetData, error) {
    batch := make([]BetData, 0, bp.batchMaxSize)
    
    for i := 0; i < bp.batchMaxSize; i++ {
        record, err := reader.Read()
        if err == io.EOF {
            log.Infof("action: read_batch | result: eof | client_id: %v", 
                bp.clientID)
            break
        }
        if err != nil {
            log.Errorf("action: read_record | result: error | client_id: %v | error: %v", 
                bp.clientID, err)
            return batch, fmt.Errorf("error reading CSV record: %v", err)
        }
                
        if len(record) >= RECORD_MAX_SIZE {
            batch = append(batch, createBetDataFromRecord(record))
        } else {
            log.Warningf("action: process_record | result: skip | client_id: %v | reason: insufficient_fields | fields: %d | required: %d", 
                bp.clientID, len(record), RECORD_MAX_SIZE)
        }
    }
    
    if len(batch) == 0 {
        return nil, io.EOF
    }
    
    return batch, nil
}

// converts the bet batch into the format used to send data
func (bp *BatchProcessor) prepareBatchForSending(batch []BetData) []map[string]string {
    result := make([]map[string]string, len(batch))
    
    for i, bet := range batch {
        result[i] = map[string]string{
            "NOMBRE":     bet.Nombre,
            "APELLIDO":   bet.Apellido,
            "DOCUMENTO":  bet.Documento,
            "NACIMIENTO": bet.Nacimiento,
            "NUMERO":     bet.Numero,
        }
    }
    
    return result
}

// prepares a formated batch to send
func (bp *BatchProcessor) SendBatch(conn net.Conn, batch []BetData) error {
    // formatted
    betsData := bp.prepareBatchForSending(batch)
    
    // communication protocol
    return SendBatchMessage(conn, len(batch), betsData)
}
