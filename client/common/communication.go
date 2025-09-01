package common

import (
	"encoding/binary"
	"errors"
	"fmt"
	"io"
	"net"
	"strings"
)

const (
    HEADER_SIZE     = 4
    FIELD_SEPARATOR = "|"
    KEY_VALUE_SEPARATOR    = ":"
    END_MARKER      = "\n"
    KEY = 0
    VALUE = 1
    ZERO_BYTES = 0
)

// escapes special characters into a value
func escapeSpecialChars(value string) string {
    value = strings.ReplaceAll(value, FIELD_SEPARATOR, "\\" + FIELD_SEPARATOR)
    value = strings.ReplaceAll(value, KEY_VALUE_SEPARATOR, "\\" + KEY_VALUE_SEPARATOR)
    return value
}

// serializes a dictionary into a string with separated fields
func serializeData(data map[string]string) string {
    var builder strings.Builder
    
    i := 0
    for key, value := range data {
        escapedValue := escapeSpecialChars(value)
        
        if i > 0 {
            builder.WriteString(FIELD_SEPARATOR)
        }
        builder.WriteString(fmt.Sprintf("%s%s%s", key, KEY_VALUE_SEPARATOR, escapedValue))
        i++
    }
    
    builder.WriteString(END_MARKER)

    return builder.String()
}

// serializes a batch of bets
func serializeBatchData(batchSize int, bets []map[string]string) string {
    var builder strings.Builder
    
    builder.WriteString(fmt.Sprintf("BATCH_SIZE%s%d", KEY_VALUE_SEPARATOR, batchSize))
    
    for i, bet := range bets {
        betStr := serializeData(bet)
        betStr = strings.TrimSuffix(betStr, END_MARKER)
        
        builder.WriteString(FIELD_SEPARATOR)
        builder.WriteString(fmt.Sprintf("BET_%d%s%s", i+1, KEY_VALUE_SEPARATOR, betStr))
    }
    
    builder.WriteString(END_MARKER)
    
    return builder.String()
}

// deserializes a string into a dictionary
func deserializeData(dataStr string) map[string]string {
    result := make(map[string]string)
    
    dataStr = strings.TrimSuffix(dataStr, END_MARKER)
    
    var fields []string
    escape := false
    currentField := ""
    
    for _, char := range dataStr {
        if escape {
            currentField += string(char)
            escape = false
        } else if char == '\\' {
            escape = true
        } else if string(char) == FIELD_SEPARATOR {
            fields = append(fields, currentField)
            currentField = ""
        } else {
            currentField += string(char)
        }
    }
    
    if currentField != "" {
        fields = append(fields, currentField)
    }
    
    for _, field := range fields {
        if strings.Contains(field, KEY_VALUE_SEPARATOR) {
            parts := strings.SplitN(field, KEY_VALUE_SEPARATOR, 2)
            result[parts[KEY]] = parts[VALUE]
        }
    }
    
    return result
}

// write N (data) bytes through the socket
func writeExactBytes(conn net.Conn, data []byte) error {
    totalSent := ZERO_BYTES
    for totalSent < len(data) {
        sent, err := conn.Write(data[totalSent:])
        if err != nil {
            return err
        }
        if sent == ZERO_BYTES {
            return errors.New("socket connection broken")
        }
        totalSent += sent
    }
    return nil
}

// sends a serialized message through the socket
func sendSerializedMessage(conn net.Conn, serializedMessage string) error {
    if conn == nil {
        return errors.New("connection is nil")
    }
    
    messageBytes := []byte(serializedMessage)
    
    lengthPrefix := make([]byte, HEADER_SIZE)
    binary.BigEndian.PutUint32(lengthPrefix, uint32(len(messageBytes)))
    
    // send length prefix
    if err := writeExactBytes(conn, lengthPrefix); err != nil {
        return err
    }
    
    // send payload
    return writeExactBytes(conn, messageBytes)
}

// sends batch of bets data through the socket
func SendBatchMessage(conn net.Conn, batchSize int, bets []map[string]string) error {
    message := serializeBatchData(batchSize, bets)
    return sendSerializedMessage(conn, message)
}

// read N (size) bytes from the socket
func readExactBytes(conn net.Conn, size int) ([]byte, error) {
    buffer := make([]byte, size)
    totalRead := ZERO_BYTES
    
    for totalRead < size {
        n, err := conn.Read(buffer[totalRead:])
        if err != nil {
            if err == io.EOF && totalRead == ZERO_BYTES {
                return nil, errors.New("connection closed by peer")
            }
            return nil, err
        }
        if n == ZERO_BYTES {
            return nil, errors.New("connection closed before receiving complete data")
        }
        totalRead += n
    }
    
    return buffer, nil
}

// receives a message from the socket
func ReceiveMessage(conn net.Conn) (map[string]string, error) {    
    // read length prefix
    lengthBytes, err := readExactBytes(conn, HEADER_SIZE)
    if err != nil {
        return nil, err
    }
    
    messageLength := binary.BigEndian.Uint32(lengthBytes)
    
    // read payload
    messageBytes, err := readExactBytes(conn, int(messageLength))
    if err != nil {
        return nil, err
    }
    
    messageStr := string(messageBytes)

    return deserializeData(messageStr), nil
}
