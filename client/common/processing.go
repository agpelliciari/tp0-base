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

// reads all the bets registered in the csv file
func (bp *BatchProcessor) ReadBetsFromCSV() ([]BetData, error) {
    filePath := filepath.Join(".data", fmt.Sprintf("agency-%s.csv", bp.clientID))

    if _, err := os.Stat(filePath); os.IsNotExist(err) {
        return nil, fmt.Errorf("CSV file not found for client %s: %v", bp.clientID, err)
    }
    
    file, err := os.Open(filePath)
    if err != nil {
        return nil, fmt.Errorf("error opening CSV file: %v", err)
    }
    defer file.Close()
    
    reader := csv.NewReader(file)
    reader.Comma = ','
    
    // Leer y descartar encabezados
    if _, err = reader.Read(); err != nil {
        return nil, fmt.Errorf("error reading CSV headers: %v", err)
    }
    
    var bets []BetData
    
    for {
        record, err := reader.Read()
        if err == io.EOF {
            break
        }
        if err != nil {
            return nil, fmt.Errorf("error reading CSV record: %v", err)
        }
        
        if len(record) >= RECORD_MAX_SIZE {
            bets = append(bets, createBetDataFromRecord(record))
        }
    }
    
    return bets, nil
}

// divides the bets in batches based on the config file
func (bp *BatchProcessor) CreateBatches(allBets []BetData) [][]BetData {
    var batches [][]BetData
    
    for i := 0; i < len(allBets); i += bp.batchMaxSize {
        end := i + bp.batchMaxSize
        if end > len(allBets) {
            end = len(allBets)
        }
        batches = append(batches, allBets[i:end])
    }
    
    return batches
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
