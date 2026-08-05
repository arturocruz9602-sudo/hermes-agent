package main

import (
	"bufio"
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"net"
	"net/http"
	"os"
	"os/exec"
	"os/user"
	"runtime"
	"strings"
	"sync"
	"time"
)

const (
	ntfyBase = "https://ntfy.sh/"
	prefix   = "HERMES_MSG::"
)

type HelloMessage struct {
	Type     string `json:"type"`
	DeviceID string `json:"device_id"`
	OS       string `json:"os"`
	IPLocal  string `json:"ip_local"`
}

type ExecApproval struct {
	Type      string `json:"type"`
	SessionID string `json:"session_id"`
	DeviceID  string `json:"device_id"`
	Command   string `json:"command"`
}

type ExecResult struct {
	Type      string `json:"type"`
	SessionID string `json:"session_id"`
	DeviceID  string `json:"device_id"`
	Command   string `json:"command"`
	Output    string `json:"output"`
	ExitCode  int    `json:"exit_code"`
	Success   bool   `json:"success"`
}

type ntfyMessage struct {
	Event   string `json:"event"`
	Message string `json:"message"`
}

var (
	procesadosMutex sync.Mutex
	procesados      = map[string]bool{}
)

func main() {
	topic := os.Getenv("HERMES_NTFY_TOPIC")

	if topic == "" {
		fmt.Println("❌ Falta la variable de entorno HERMES_NTFY_TOPIC")
		os.Exit(1)
	}

	deviceID := getDeviceID()
	fmt.Printf("🔑 device_id generado: %s\n", deviceID)

	hello := HelloMessage{
		Type:     "hello",
		DeviceID: deviceID,
		OS:       runtime.GOOS,
		IPLocal:  getLocalIP(),
	}

	if err := publishGeneric(topic, hello); err != nil {
		fmt.Printf("❌ Error mandando hello: %v\n", err)
		os.Exit(1)
	}
	fmt.Println("✅ Mensaje hello publicado en ntfy.sh. Revisa Telegram para la confirmación del gateway.")
	fmt.Println("👂 Escuchando comandos aprobados para este dispositivo... (Ctrl+C para detener)")

	listenForApprovals(topic, deviceID)
}

// getDeviceID genera un identificador único y estable por máquina,
// combinando el hostname (legible) con un ID de hardware único
// (machine-id en Linux, MachineGuid en Windows, IOPlatformUUID en Mac).
// Si no logra leer el ID de hardware, cae de vuelta a hostname+usuario
// (comportamiento anterior) para nunca bloquear el arranque del agente.
func getDeviceID() string {
	hostname, err := os.Hostname()
	if err != nil {
		hostname = "desconocido"
	}

	hardwareID, err := getHardwareID()
	if err != nil {
		// Fallback: comportamiento anterior, por si el hardware ID falla
		currentUser, errUser := user.Current()
		username := "desconocido"
		if errUser == nil {
			username = currentUser.Username
		}
		fmt.Printf("⚠️  No se pudo leer ID de hardware (%v), usando fallback hostname+usuario\n", err)
		return fmt.Sprintf("%s-%s", hostname, username)
	}

	// Combina hostname + hardwareID y saca un hash corto, estable y único
	combinado := hostname + "|" + hardwareID
	suma := sha256.Sum256([]byte(combinado))
	hashCorto := hex.EncodeToString(suma[:])[:12]

	return fmt.Sprintf("%s-%s", hostname, hashCorto)
}

// getHardwareID obtiene un identificador único de la máquina física,
// según el sistema operativo detectado en tiempo de ejecución.
func getHardwareID() (string, error) {
	switch runtime.GOOS {
	case "linux":
		return leerArchivoLimpio("/etc/machine-id", "/var/lib/dbus/machine-id")
	case "windows":
		out, err := exec.Command("reg", "query",
			`HKLM\SOFTWARE\Microsoft\Cryptography`, "/v", "MachineGuid").Output()
		if err != nil {
			return "", err
		}
		return extraerUltimoCampo(string(out)), nil
	case "darwin":
		out, err := exec.Command("ioreg", "-rd1", "-c", "IOPlatformExpertDevice").Output()
		if err != nil {
			return "", err
		}
		return extraerIOPlatformUUID(string(out))
	default:
		return "", fmt.Errorf("sistema operativo no soportado para hardware ID: %s", runtime.GOOS)
	}
}

func leerArchivoLimpio(rutas ...string) (string, error) {
	var ultimoErr error
	for _, ruta := range rutas {
		data, err := os.ReadFile(ruta)
		if err == nil {
			return strings.TrimSpace(string(data)), nil
		}
		ultimoErr = err
	}
	return "", ultimoErr
}

func extraerUltimoCampo(texto string) string {
	lineas := strings.Split(strings.TrimSpace(texto), "\n")
	ultima := lineas[len(lineas)-1]
	campos := strings.Fields(ultima)
	if len(campos) == 0 {
		return ""
	}
	return campos[len(campos)-1]
}

func extraerIOPlatformUUID(texto string) (string, error) {
	for _, linea := range strings.Split(texto, "\n") {
		if strings.Contains(linea, "IOPlatformUUID") {
			partes := strings.Split(linea, "\"")
			if len(partes) >= 4 {
				return partes[3], nil
			}
		}
	}
	return "", fmt.Errorf("no se encontró IOPlatformUUID en la salida de ioreg")
}

func getLocalIP() string {
	conn, err := net.Dial("udp", "8.8.8.8:80")
	if err != nil {
		return "desconocida"
	}
	defer conn.Close()
	localAddr := conn.LocalAddr().(*net.UDPAddr)
	return localAddr.IP.String()
}

func publishGeneric(topic string, payload interface{}) error {
	data, err := json.Marshal(payload)
	if err != nil {
		return err
	}
	text := prefix + string(data)

	url := ntfyBase + topic
	resp, err := http.Post(url, "text/plain", bytes.NewBufferString(text))
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	body, _ := io.ReadAll(resp.Body)
	if resp.StatusCode != 200 {
		return fmt.Errorf("ntfy.sh respondió %d: %s", resp.StatusCode, string(body))
	}
	return nil
}

func listenForApprovals(topic, deviceID string) {
	url := ntfyBase + topic + "/json"

	for {
		resp, err := http.Get(url)
		if err != nil {
			fmt.Printf("⚠️  Error conectando a ntfy: %v (reintentando en 3s)\n", err)
			time.Sleep(3 * time.Second)
			continue
		}

		scanner := bufio.NewScanner(resp.Body)
		for scanner.Scan() {
			line := scanner.Text()
			if line == "" {
				continue
			}

			var msg ntfyMessage
			if err := json.Unmarshal([]byte(line), &msg); err != nil {
				continue
			}
			if msg.Event != "message" || msg.Message == "" {
				continue
			}
			if !strings.HasPrefix(msg.Message, prefix) {
				continue
			}

			payloadRaw := msg.Message[len(prefix):]

			var generic map[string]interface{}
			if err := json.Unmarshal([]byte(payloadRaw), &generic); err != nil {
				continue
			}
			tipo, _ := generic["type"].(string)
			if tipo != "exec_approved" {
				continue
			}

			var approval ExecApproval
			if err := json.Unmarshal([]byte(payloadRaw), &approval); err != nil {
				continue
			}

			if approval.DeviceID != deviceID {
				continue // no es para este dispositivo
			}

			procesadosMutex.Lock()
			yaProcesado := procesados[approval.SessionID]
			if !yaProcesado {
				procesados[approval.SessionID] = true
			}
			procesadosMutex.Unlock()

			if yaProcesado {
				continue // evita re-ejecutar si el evento llega duplicado
			}

			fmt.Printf("▶️  Ejecutando comando aprobado (session_id=%s): %s\n", approval.SessionID, approval.Command)
			ejecutarYReportar(topic, approval)
		}

		resp.Body.Close()
		fmt.Println("⚠️  Conexión a ntfy cerrada, reconectando en 2s...")
		time.Sleep(2 * time.Second)
	}
}

func ejecutarYReportar(topic string, approval ExecApproval) {
	var cmd *exec.Cmd
	if runtime.GOOS == "windows" {
		cmd = exec.Command("cmd", "/C", approval.Command)
	} else {
		cmd = exec.Command("sh", "-c", approval.Command)
	}

	output, err := cmd.CombinedOutput()

	exitCode := 0
	success := true
	if err != nil {
		success = false
		if exitErr, ok := err.(*exec.ExitError); ok {
			exitCode = exitErr.ExitCode()
		} else {
			exitCode = -1
		}
	}

	outStr := string(output)
	if len(outStr) > 3000 {
		outStr = outStr[:3000] + "\n...(truncado)"
	}

	result := ExecResult{
		Type:      "exec_result",
		SessionID: approval.SessionID,
		DeviceID:  approval.DeviceID,
		Command:   approval.Command,
		Output:    outStr,
		ExitCode:  exitCode,
		Success:   success,
	}

	fmt.Printf("✅ Ejecución terminada (exit_code=%d, success=%v)\n", exitCode, success)

	if err := publishGeneric(topic, result); err != nil {
		fmt.Printf("⚠️  Error publicando exec_result: %v\n", err)
	}
}
