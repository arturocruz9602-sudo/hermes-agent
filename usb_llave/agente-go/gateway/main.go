package main

import (
	"bufio"
	"crypto/rand"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"os"
	"regexp"
	"strconv"
	"strings"
	"sync"
	"time"
)

const (
	telegramAPIBase = "https://api.telegram.org/bot"
	ntfyBase        = "https://ntfy.sh/"
	prefix          = "HERMES_MSG::"
	dbFile          = "dispositivos.json"
)

var patronesPeligrosos = []struct {
	patron *regexp.Regexp
	motivo string
}{
	{regexp.MustCompile(`rm\s+-rf\s+/`), "borrado recursivo forzado de raíz o rutas amplias"},
	{regexp.MustCompile(`rm\s+-rf\s+~`), "borrado recursivo forzado del home"},
	{regexp.MustCompile(`mkfs`), "formateo de sistema de archivos"},
	{regexp.MustCompile(`dd\s+.*of=/dev/`), "escritura directa a dispositivo de bloque"},
	{regexp.MustCompile(`:\(\)\s*\{\s*:\|:&\s*\};`), "fork bomb"},
	{regexp.MustCompile(`chmod\s+-r\s+777\s+/`), "permisos 777 recursivos sobre raíz"},
	{regexp.MustCompile(`>\s*/dev/sd[a-z]`), "sobrescritura directa de disco"},
	{regexp.MustCompile(`shutdown|poweroff|reboot`), "apagado/reinicio del sistema"},
	{regexp.MustCompile(`del\s+/s\s+/q\s+c:\\`), "borrado recursivo forzado en Windows (C:\\)"},
	{regexp.MustCompile(`format\s+c:`), "formateo de unidad C: en Windows"},
	{regexp.MustCompile(`net\s+user.*\/add`), "creación de usuario del sistema"},
	{regexp.MustCompile(`passwd\s`), "cambio de contraseña del sistema"},
}

func evaluarComando(cmd string) (bool, string) {
	normalizado := strings.ToLower(strings.TrimSpace(cmd))
	for _, p := range patronesPeligrosos {
		if p.patron.MatchString(normalizado) {
			return false, p.motivo
		}
	}
	return true, ""
}

type PendingConfirm struct {
	SessionID string
	DeviceID  string
	Action    string
	Reason    string
	Approved  *bool
}

var (
	pendientesMutex sync.Mutex
	pendientes      = map[string]*PendingConfirm{}
)

func nuevoSessionID() string {
	b := make([]byte, 6)
	_, _ = rand.Read(b)
	return hex.EncodeToString(b)
}

type Dispositivo struct {
	DeviceID       string `json:"device_id"`
	OS             string `json:"os"`
	IPLocal        string `json:"ip_local"`
	FirstSeen      string `json:"first_seen"`
	LastSeen       string `json:"last_seen"`
	Connected      bool   `json:"connected"`
	DisconnectedAt string `json:"disconnected_at,omitempty"`
}

type HelloPayload struct {
	Type     string `json:"type"`
	DeviceID string `json:"device_id"`
	OS       string `json:"os"`
	IPLocal  string `json:"ip_local"`
}

type ByePayload struct {
	Type     string `json:"type"`
	DeviceID string `json:"device_id"`
}

type ExecApproval struct {
	Type      string `json:"type"`
	SessionID string `json:"session_id"`
	DeviceID  string `json:"device_id"`
	Command   string `json:"command"`
}

var dbMutex sync.Mutex

// deviceIDLocalHP identifica a ESTA máquina (donde corre el gateway) con el
// mismo algoritmo que usa el agente (hostname + hash de machine-id) -- antes
// era un string hardcodeado, lo que rompía silencioso el ruteo "sin alias
// va a la HP" si el machine-id de la HP cambiaba (reinstalación, etc.).
// Se calcula una sola vez al arrancar (comportamiento de var de paquete).
var deviceIDLocalHP = computeDeviceIDLocal()

func computeDeviceIDLocal() string {
	hostname, err := os.Hostname()
	if err != nil {
		hostname = "hp-local"
	}

	hardwareID, err := leerArchivoLimpio("/etc/machine-id", "/var/lib/dbus/machine-id")
	if err != nil {
		// Fallback: sin machine-id legible, usa solo el hostname. Sigue siendo
		// estable entre corridas en la misma máquina, aunque menos único.
		return hostname
	}

	suma := sha256.Sum256([]byte(hostname + "|" + hardwareID))
	hashCorto := hex.EncodeToString(suma[:])[:12]
	return fmt.Sprintf("%s-%s", hostname, hashCorto)
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

func main() {
	telegramToken := os.Getenv("HERMES_DISPOSITIVOS_TOKEN")
	chatIDStr := os.Getenv("HERMES_CHAT_ID")
	ntfyTopic := os.Getenv("HERMES_NTFY_TOPIC")

	if telegramToken == "" || chatIDStr == "" || ntfyTopic == "" {
		fmt.Println("❌ Faltan variables: HERMES_DISPOSITIVOS_TOKEN, HERMES_CHAT_ID y/o HERMES_NTFY_TOPIC")
		os.Exit(1)
	}

	chatID, err := strconv.ParseInt(chatIDStr, 10, 64)
	if err != nil {
		fmt.Printf("❌ HERMES_CHAT_ID inválido: %v\n", err)
		os.Exit(1)
	}

	if err := ensureDBFile(); err != nil {
		fmt.Printf("❌ Error preparando %s: %v\n", dbFile, err)
		os.Exit(1)
	}

	fmt.Println("✅ Hermes Gateway (Go, v4) iniciado.")
	fmt.Printf("   Escuchando ntfy.sh en tema: %s\n", ntfyTopic)
	fmt.Println("   Escuchando Telegram para tus mensajes/confirmaciones.")
	fmt.Println("   💡 Prueba: test: <comando>              → apunta a la HP por default")
	fmt.Println("   💡 Prueba: test: alias: <comando>       → busca 'alias' en dispositivos.json")
	fmt.Println("   Ctrl+C para detener.")

	var wg sync.WaitGroup
	wg.Add(2)

	go func() {
		defer wg.Done()
		listenNtfy(ntfyTopic, telegramToken, chatID)
	}()

	go func() {
		defer wg.Done()
		listenTelegramForever(telegramToken, chatID, ntfyTopic)
	}()

	wg.Wait()
}

func ensureDBFile() error {
	if _, err := os.Stat(dbFile); os.IsNotExist(err) {
		return writeAll(map[string]Dispositivo{})
	}
	return nil
}

func writeAll(dispositivos map[string]Dispositivo) error {
	data, err := json.MarshalIndent(dispositivos, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(dbFile, data, 0600)
}

func leerTodosLosDispositivos() (map[string]Dispositivo, error) {
	dbMutex.Lock()
	defer dbMutex.Unlock()

	data, err := os.ReadFile(dbFile)
	if err != nil {
		return nil, err
	}
	dispositivos := map[string]Dispositivo{}
	if len(data) > 0 {
		if err := json.Unmarshal(data, &dispositivos); err != nil {
			return nil, err
		}
	}
	return dispositivos, nil
}

// resolverAlias busca un alias (ej. "almendra") como substring dentro
// de los device_id ya registrados en dispositivos.json (sin importar
// mayúsculas/minúsculas). Si encuentra exactamente una coincidencia,
// la devuelve. Si no encuentra ninguna o encuentra varias, devuelve error.
func resolverAlias(alias string) (string, error) {
	dispositivos, err := leerTodosLosDispositivos()
	if err != nil {
		return "", fmt.Errorf("no pude leer dispositivos.json: %v", err)
	}

	aliasNormalizado := strings.ToLower(strings.TrimSpace(alias))
	var coincidencias []string

	for deviceID := range dispositivos {
		if strings.Contains(strings.ToLower(deviceID), aliasNormalizado) {
			coincidencias = append(coincidencias, deviceID)
		}
	}

	if len(coincidencias) == 0 {
		return "", fmt.Errorf("no encontré ningún dispositivo registrado que contenga '%s'", alias)
	}
	if len(coincidencias) > 1 {
		return "", fmt.Errorf("el alias '%s' coincide con varios dispositivos: %s (sé más específico)",
			alias, strings.Join(coincidencias, ", "))
	}

	return coincidencias[0], nil
}

func registrarDispositivo(deviceID, osName, ipLocal string) (bool, error) {
	dbMutex.Lock()
	defer dbMutex.Unlock()

	data, err := os.ReadFile(dbFile)
	if err != nil {
		return false, err
	}

	dispositivos := map[string]Dispositivo{}
	if len(data) > 0 {
		if err := json.Unmarshal(data, &dispositivos); err != nil {
			return false, err
		}
	}

	ahora := time.Now().UTC().Format(time.RFC3339)
	existente, yaExiste := dispositivos[deviceID]

	nuevo := Dispositivo{
		DeviceID:  deviceID,
		OS:        osName,
		IPLocal:   ipLocal,
		FirstSeen: ahora,
		LastSeen:  ahora,
		Connected: true,
	}
	if yaExiste {
		nuevo.FirstSeen = existente.FirstSeen
	}

	dispositivos[deviceID] = nuevo

	if err := writeAll(dispositivos); err != nil {
		return false, err
	}

	return !yaExiste, nil
}

// marcarDesconectado deja constancia en dispositivos.json de que un
// dispositivo mandó "bye" -- el "resumen guardado" mínimo que pedía la
// Fase 4 del checklist (sin memoria/contexto todavía, eso vive en la HP
// según la arquitectura aprobada, no en el canal de transporte).
func marcarDesconectado(deviceID string) error {
	dbMutex.Lock()
	defer dbMutex.Unlock()

	data, err := os.ReadFile(dbFile)
	if err != nil {
		return err
	}

	dispositivos := map[string]Dispositivo{}
	if len(data) > 0 {
		if err := json.Unmarshal(data, &dispositivos); err != nil {
			return err
		}
	}

	dispositivo, existe := dispositivos[deviceID]
	if !existe {
		return fmt.Errorf("bye de dispositivo no registrado: %s", deviceID)
	}

	dispositivo.Connected = false
	dispositivo.DisconnectedAt = time.Now().UTC().Format(time.RFC3339)
	dispositivos[deviceID] = dispositivo

	return writeAll(dispositivos)
}

type ntfyMessage struct {
	Event   string `json:"event"`
	Message string `json:"message"`
}

func listenNtfy(topic, telegramToken string, chatID int64) {
	url := ntfyBase + topic + "/json"

	for {
		resp, err := http.Get(url)
		if err != nil {
			fmt.Printf("⚠️  [ntfy] Error conectando: %v (reintentando en 3s)\n", err)
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

			procesarMensajeNtfy(msg.Message, telegramToken, chatID)
		}

		resp.Body.Close()
		fmt.Println("⚠️  [ntfy] Conexión cerrada, reconectando en 2s...")
		time.Sleep(2 * time.Second)
	}
}

func procesarMensajeNtfy(texto, telegramToken string, chatID int64) {
	if len(texto) < len(prefix) || texto[:len(prefix)] != prefix {
		return
	}

	payloadRaw := texto[len(prefix):]

	var generic map[string]interface{}
	if err := json.Unmarshal([]byte(payloadRaw), &generic); err != nil {
		fmt.Printf("⚠️  [ntfy] JSON inválido: %v\n", err)
		return
	}

	tipo, _ := generic["type"].(string)

	switch tipo {
	case "hello":
		manejarHello(telegramToken, chatID, payloadRaw)
	case "exec_result":
		manejarExecResult(telegramToken, chatID, payloadRaw)
	case "bye":
		manejarBye(telegramToken, chatID, payloadRaw)
	default:
		fmt.Printf("ℹ️  [ntfy] Tipo de mensaje aún no soportado: %s\n", tipo)
	}
}

func manejarBye(telegramToken string, chatID int64, payloadRaw string) {
	var bye ByePayload
	if err := json.Unmarshal([]byte(payloadRaw), &bye); err != nil {
		fmt.Printf("⚠️  Error parseando bye: %v\n", err)
		return
	}

	fmt.Printf("📥 [ntfy] bye recibido — device_id=%s\n", bye.DeviceID)

	if err := marcarDesconectado(bye.DeviceID); err != nil {
		fmt.Printf("⚠️  Error marcando desconexión: %v\n", err)
	}

	_ = sendTelegramMessage(telegramToken, chatID, fmt.Sprintf(
		"👋 Dispositivo desconectado.\ndevice_id: %s", bye.DeviceID))
}

func manejarHello(telegramToken string, chatID int64, payloadRaw string) {
	var hello HelloPayload
	if err := json.Unmarshal([]byte(payloadRaw), &hello); err != nil {
		fmt.Printf("⚠️  Error parseando hello: %v\n", err)
		return
	}

	esNuevo, err := registrarDispositivo(hello.DeviceID, hello.OS, hello.IPLocal)
	if err != nil {
		fmt.Printf("⚠️  Error registrando dispositivo: %v\n", err)
		return
	}

	fmt.Printf("📥 [ntfy] hello recibido — device_id=%s, nuevo=%v\n", hello.DeviceID, esNuevo)

	var respuesta string
	if esNuevo {
		respuesta = fmt.Sprintf(
			"🔌 Nueva sesión conectada.\ndevice_id: %s\nOS: %s\nIP local: %s",
			hello.DeviceID, hello.OS, hello.IPLocal)
	} else {
		respuesta = fmt.Sprintf(
			"🔄 Dispositivo reconocido (sesión anterior).\ndevice_id: %s\nOS: %s\nIP local: %s",
			hello.DeviceID, hello.OS, hello.IPLocal)
	}

	_ = sendTelegramMessage(telegramToken, chatID, respuesta)
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

func manejarExecResult(telegramToken string, chatID int64, payloadRaw string) {
	var result ExecResult
	if err := json.Unmarshal([]byte(payloadRaw), &result); err != nil {
		fmt.Printf("⚠️  Error parseando exec_result: %v\n", err)
		return
	}

	fmt.Printf("📥 [ntfy] exec_result recibido — session_id=%s, success=%v, exit_code=%d\n",
		result.SessionID, result.Success, result.ExitCode)

	icono := "✅"
	if !result.Success {
		icono = "❌"
	}

	salida := strings.TrimSpace(result.Output)
	if salida == "" {
		salida = "(sin salida)"
	}

	texto := fmt.Sprintf(
		"%s Resultado de ejecución en `%s`:\n\nComando: `%s`\nExit code: %d\n\nSalida:\n```\n%s\n```",
		icono, result.DeviceID, result.Command, result.ExitCode, salida)

	_ = sendTelegramMessage(telegramToken, chatID, texto)
}

func sendTelegramMessage(token string, chatID int64, text string) error {
	apiURL := fmt.Sprintf("%s%s/sendMessage", telegramAPIBase, token)
	form := url.Values{}
	form.Set("chat_id", fmt.Sprintf("%d", chatID))
	form.Set("text", text)

	resp, err := http.PostForm(apiURL, form)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	body, _ := io.ReadAll(resp.Body)
	if resp.StatusCode != 200 {
		return fmt.Errorf("Telegram respondió %d: %s", resp.StatusCode, string(body))
	}
	return nil
}

func publishNtfy(topic, message string) error {
	apiURL := ntfyBase + topic
	resp, err := http.Post(apiURL, "text/plain", strings.NewReader(message))
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 {
		body, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("ntfy publish respondió %d: %s", resp.StatusCode, string(body))
	}
	return nil
}

func requierePrivilegiosElevados(cmd string) bool {
	normalizado := strings.ToLower(strings.TrimSpace(cmd))
	prefijosAdmin := []string{"sudo ", "sudo\t", "runas ", "doas "}
	for _, p := range prefijosAdmin {
		if strings.HasPrefix(normalizado, p) {
			return true
		}
	}
	return false
}

func sendConfirmRequest(token string, chatID int64, sessionID, action, reason string) error {
	apiURL := fmt.Sprintf("%s%s/sendMessage", telegramAPIBase, token)

	advertencia := ""
	if requierePrivilegiosElevados(action) {
		advertencia = "⚠️ *Este comando requiere privilegios de administrador (sudo).*\n\n"
	}

	texto := fmt.Sprintf(
		"%s🤔 Hermes propone ejecutar:\n\n`%s`\n\nMotivo: %s\n\n¿Autorizas?",
		advertencia, action, reason)

	replyMarkup := map[string]interface{}{
		"inline_keyboard": [][]map[string]string{
			{
				{"text": "✅ Sí", "callback_data": sessionID + ":yes"},
				{"text": "❌ No", "callback_data": sessionID + ":no"},
			},
		},
	}
	replyMarkupJSON, _ := json.Marshal(replyMarkup)

	form := url.Values{}
	form.Set("chat_id", fmt.Sprintf("%d", chatID))
	form.Set("text", texto)
	form.Set("parse_mode", "Markdown")
	form.Set("reply_markup", string(replyMarkupJSON))

	resp, err := http.PostForm(apiURL, form)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	body, _ := io.ReadAll(resp.Body)
	if resp.StatusCode != 200 {
		return fmt.Errorf("Telegram respondió %d: %s", resp.StatusCode, string(body))
	}
	return nil
}

func answerCallbackQuery(token, callbackQueryID, texto string) error {
	apiURL := fmt.Sprintf("%s%s/answerCallbackQuery", telegramAPIBase, token)
	form := url.Values{}
	form.Set("callback_query_id", callbackQueryID)
	form.Set("text", texto)

	resp, err := http.PostForm(apiURL, form)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	return nil
}

func proponerAccion(token string, chatID int64, deviceID, action, reason string) {
	permitido, motivoBloqueo := evaluarComando(action)

	if !permitido {
		fmt.Printf("🚫 Comando bloqueado por lista negra: %s (%s)\n", action, motivoBloqueo)
		_ = sendTelegramMessage(token, chatID, fmt.Sprintf(
			"🚫 No voy a proponer este comando, está en la lista negra.\n\nComando: `%s`\nRazón del bloqueo: %s",
			action, motivoBloqueo))
		return
	}

	sessionID := nuevoSessionID()

	pendientesMutex.Lock()
	pendientes[sessionID] = &PendingConfirm{
		SessionID: sessionID,
		DeviceID:  deviceID,
		Action:    action,
		Reason:    reason,
	}
	pendientesMutex.Unlock()

	fmt.Printf("❓ Propuesta enviada — session_id=%s, device_id=%s, action=%s\n", sessionID, deviceID, action)

	if err := sendConfirmRequest(token, chatID, sessionID, action, reason); err != nil {
		fmt.Printf("⚠️  Error mandando confirm_request: %v\n", err)
	}
}

type updateResult struct {
	OK     bool `json:"ok"`
	Result []struct {
		UpdateID int `json:"update_id"`
		Message  struct {
			Text string `json:"text"`
			Chat struct {
				ID int64 `json:"id"`
			} `json:"chat"`
		} `json:"message"`
		CallbackQuery struct {
			ID      string `json:"id"`
			Data    string `json:"data"`
			Message struct {
				Chat struct {
					ID int64 `json:"id"`
				} `json:"chat"`
			} `json:"message"`
		} `json:"callback_query"`
	} `json:"result"`
}

// parsearComandoDeTest interpreta el texto después de "test:".
// Si viene con formato "alias: comando", intenta resolver el alias.
// Si no, usa el device_id default de la HP (comportamiento anterior).
func parsearComandoDeTest(texto string) (deviceID string, comando string, avisoAlias string) {
	// Busca un patrón "algo:" al inicio (el alias), seguido del resto (el comando)
	patronAlias := regexp.MustCompile(`^([A-Za-z0-9_\-]+):\s*(.+)$`)
	match := patronAlias.FindStringSubmatch(texto)

	if match == nil {
		// No trae alias, comportamiento anterior: todo es el comando, va a la HP
		return deviceIDLocalHP, texto, ""
	}

	posibleAlias := match[1]
	resto := match[2]

	deviceIDResuelto, err := resolverAlias(posibleAlias)
	if err != nil {
		// No se pudo resolver como alias — tratamos TODO el texto como comando
		// dirigido a la HP por default, y avisamos por qué.
		return deviceIDLocalHP, texto, fmt.Sprintf(
			"ℹ️ No interpreté '%s' como alias de dispositivo (%v) — mandando a la HP por default.",
			posibleAlias, err)
	}

	return deviceIDResuelto, resto, fmt.Sprintf("🎯 Alias '%s' resuelto a: %s", posibleAlias, deviceIDResuelto)
}

func listenTelegramForever(token string, defaultChatID int64, ntfyTopic string) {
	offset := 0

	for {
		apiURL := fmt.Sprintf("%s%s/getUpdates?timeout=20&offset=%d", telegramAPIBase, token, offset)
		resp, err := http.Get(apiURL)
		if err != nil {
			fmt.Printf("⚠️  [telegram] Error en getUpdates: %v (reintentando en 3s)\n", err)
			time.Sleep(3 * time.Second)
			continue
		}

		body, _ := io.ReadAll(resp.Body)
		resp.Body.Close()

		var result updateResult
		if err := json.Unmarshal(body, &result); err != nil {
			continue
		}

		for _, upd := range result.Result {
			offset = upd.UpdateID + 1

			if upd.CallbackQuery.ID != "" {
				if upd.CallbackQuery.Message.Chat.ID != defaultChatID {
					continue
				}
				manejarCallback(token, ntfyTopic, upd.CallbackQuery.ID, upd.CallbackQuery.Data, upd.CallbackQuery.Message.Chat.ID)
				continue
			}

			if upd.Message.Text == "" {
				continue
			}

			texto := upd.Message.Text
			chatID := upd.Message.Chat.ID

			if chatID != defaultChatID {
				continue
			}

			if strings.HasPrefix(texto, "test:") {
				contenido := strings.TrimSpace(strings.TrimPrefix(texto, "test:"))
				deviceID, comando, aviso := parsearComandoDeTest(contenido)

				if aviso != "" {
					_ = sendTelegramMessage(token, chatID, aviso)
				}

				proponerAccion(token, chatID, deviceID, comando, "prueba manual solicitada por ti")
				continue
			}

			fmt.Printf("💬 [telegram] Mensaje tuyo recibido: %s\n", texto)
		}
	}
}

func manejarCallback(token, ntfyTopic, callbackID, data string, chatID int64) {
	partes := strings.SplitN(data, ":", 2)
	if len(partes) != 2 {
		_ = answerCallbackQuery(token, callbackID, "⚠️ Datos de botón inválidos")
		return
	}
	sessionID, decision := partes[0], partes[1]

	pendientesMutex.Lock()
	pending, existe := pendientes[sessionID]
	pendientesMutex.Unlock()

	if !existe {
		_ = answerCallbackQuery(token, callbackID, "⚠️ Esta solicitud ya expiró o no existe")
		return
	}

	aprobado := decision == "yes"

	pendientesMutex.Lock()
	pending.Approved = &aprobado
	pendientesMutex.Unlock()

	fmt.Printf("👉 Respuesta recibida — session_id=%s, aprobado=%v\n", sessionID, aprobado)

	if aprobado {
		_ = answerCallbackQuery(token, callbackID, "✅ Aprobado")

		approval := ExecApproval{
			Type:      "exec_approved",
			SessionID: sessionID,
			DeviceID:  pending.DeviceID,
			Command:   pending.Action,
		}
		payloadJSON, _ := json.Marshal(approval)
		if err := publishNtfy(ntfyTopic, prefix+string(payloadJSON)); err != nil {
			fmt.Printf("⚠️  Error publicando exec_approved en ntfy: %v\n", err)
			_ = sendTelegramMessage(token, chatID, fmt.Sprintf(
				"✅ Autorizado: `%s`\n\n⚠️ No se pudo notificar al agente (error de red con ntfy.sh).",
				pending.Action))
		} else {
			_ = sendTelegramMessage(token, chatID, fmt.Sprintf(
				"✅ Autorizado: `%s`\n📍 Dispositivo: %s\n\n📡 Notificando al agente para que ejecute...",
				pending.Action, pending.DeviceID))
		}
	} else {
		_ = answerCallbackQuery(token, callbackID, "❌ Rechazado")
		_ = sendTelegramMessage(token, chatID, fmt.Sprintf("❌ Rechazado: `%s`", pending.Action))
	}
}
