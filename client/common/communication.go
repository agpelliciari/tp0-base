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

// serializes a dictionary into a string with separated fields
func SerializeData(data map[string]string) string {
    var builder strings.Builder
    
    i := 0
    for key, value := range data {
        escapedValue := strings.ReplaceAll(value, FIELD_SEPARATOR, "\\" + FIELD_SEPARATOR)
        escapedValue = strings.ReplaceAll(escapedValue, KEY_VALUE_SEPARATOR, "\\" + KEY_VALUE_SEPARATOR)
        
        if i > 0 {
            builder.WriteString(FIELD_SEPARATOR)
        }
        builder.WriteString(fmt.Sprintf("%s%s%s", key, KEY_VALUE_SEPARATOR, escapedValue))
        i++
    }
    
    builder.WriteString(END_MARKER)

    return builder.String()
}

// deserializes a string into a dictionary
func DeserializeData(dataStr string) map[string]string {
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

// sends a serialized message through the socket
func SendMessage(conn net.Conn, data map[string]string) error {
    message := SerializeData(data)
    messageBytes := []byte(message)
    
    lengthPrefix := make([]byte, HEADER_SIZE)
    binary.BigEndian.PutUint32(lengthPrefix, uint32(len(messageBytes)))
    
    // send length prefix
    totalSent := ZERO_BYTES
    for totalSent < HEADER_SIZE {
        sent, err := conn.Write(lengthPrefix[totalSent:])
        if err != nil {
            return err
        }
        if sent == ZERO_BYTES {
            return errors.New("socket connection broken")
        }
        totalSent += sent
    }
    
    // send payload
    totalSent = ZERO_BYTES
    for totalSent < len(messageBytes) {
        sent, err := conn.Write(messageBytes[totalSent:])
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

// receives a message from the socket
func ReceiveMessage(conn net.Conn) (map[string]string, error) {
    lengthBytes := make([]byte, HEADER_SIZE)
    totalRead := ZERO_BYTES
    
    // read length prefix
    for totalRead < HEADER_SIZE {
        n, err := conn.Read(lengthBytes[totalRead:])
        if err != nil {
            if err == io.EOF && totalRead == ZERO_BYTES {
                return nil, errors.New("connection closed by peer")
            }
            return nil, err
        }
        if n == ZERO_BYTES {
            return nil, errors.New("connection closed before receiving complete header")
        }
        totalRead += n
    }
    
    messageLength := binary.BigEndian.Uint32(lengthBytes)
    
    // read payload
    messageBytes := make([]byte, messageLength)
    totalRead = ZERO_BYTES
    
    for totalRead < int(messageLength) {
        n, err := conn.Read(messageBytes[totalRead:])
        if err != nil {
            return nil, err
        }
        if n == ZERO_BYTES {
            return nil, errors.New("connection closed before receiving complete message")
        }
        totalRead += n
    }
    
    messageStr := string(messageBytes)

    return DeserializeData(messageStr), nil
}