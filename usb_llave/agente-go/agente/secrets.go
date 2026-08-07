package main

// secrets.go -- cifrado local del tema de ntfy.sh (Fase 3 del checklist:
// "Token cifrado local (no texto plano)"). Antes vivía en texto plano en
// .env dentro de la USB; cualquiera con acceso físico a la memoria podía
// leerlo. Ahora, en la USB real, se guarda cifrado en secret.enc y solo se
// descifra en memoria al arrancar, con una passphrase que Arturo escribe.
//
// Solo librería estándar (regla del proyecto: sin dependencias externas) --
// por eso la derivación de llave es un estiramiento manual con SHA-256 en
// vez de PBKDF2/scrypt de golang.org/x/crypto. Es más débil que esas
// librerías, pero razonable para el modelo de amenaza real (USB física
// perdida/robada, no un atacante con presupuesto de cómputo dedicado).
//
// LÍMITE CONOCIDO, marcado explícito: la passphrase se escribe en texto
// visible en la terminal (bufio sobre stdin) -- ocultar el eco requiere
// llamadas de terminal específicas por sistema operativo (termios en
// Unix, consola en Windows) que la librería estándar no cubre igual en
// los tres sistemas operativos objetivo. Queda como mejora futura, no
// bloquea esta fase.

import (
	"bufio"
	"crypto/aes"
	"crypto/cipher"
	"crypto/rand"
	"crypto/sha256"
	"encoding/base64"
	"errors"
	"fmt"
	"io"
	"os"
	"strings"
)

const (
	secretFile     = "secret.enc"
	kdfSaltLen     = 16
	kdfIteraciones = 100000
)

// stdinLector es un indirection sobre os.Stdin para que las pruebas puedan
// inyectar una entrada de prueba sin bloquear esperando teclado real.
var stdinLector io.Reader = os.Stdin

func escribirSecretFile(blob string) error {
	return os.WriteFile(secretFile, []byte(blob), 0600)
}

// derivarLlave estira la passphrase con SHA-256 iterado sobre la sal, para
// que probar passphrases por fuerza bruta sea caro sin depender de una
// librería externa de KDF.
func derivarLlave(passphrase string, salt []byte) []byte {
	llave := sha256.Sum256(append([]byte(passphrase), salt...))
	for i := 0; i < kdfIteraciones; i++ {
		siguiente := sha256.Sum256(append(llave[:], salt...))
		llave = siguiente
	}
	return llave[:]
}

// encryptTopic cifra el tema con AES-256-GCM. El blob resultante (base64)
// es salt(16) || nonce(12) || ciphertext -- todo lo necesario para
// descifrar excepto la passphrase, que nunca se guarda en disco.
func encryptTopic(topic, passphrase string) (string, error) {
	salt := make([]byte, kdfSaltLen)
	if _, err := rand.Read(salt); err != nil {
		return "", fmt.Errorf("generando sal: %w", err)
	}

	block, err := aes.NewCipher(derivarLlave(passphrase, salt))
	if err != nil {
		return "", err
	}
	gcm, err := cipher.NewGCM(block)
	if err != nil {
		return "", err
	}

	nonce := make([]byte, gcm.NonceSize())
	if _, err := rand.Read(nonce); err != nil {
		return "", fmt.Errorf("generando nonce: %w", err)
	}

	ciphertext := gcm.Seal(nil, nonce, []byte(topic), nil)

	blob := make([]byte, 0, len(salt)+len(nonce)+len(ciphertext))
	blob = append(blob, salt...)
	blob = append(blob, nonce...)
	blob = append(blob, ciphertext...)

	return base64.StdEncoding.EncodeToString(blob), nil
}

// decryptTopic revierte encryptTopic. Una passphrase incorrecta o un
// archivo corrupto fallan explícito (GCM autentica) -- nunca devuelve
// basura silenciosa como si fuera el tema real.
func decryptTopic(blobB64, passphrase string) (string, error) {
	blob, err := base64.StdEncoding.DecodeString(strings.TrimSpace(blobB64))
	if err != nil {
		return "", fmt.Errorf("secret.enc no es base64 válido: %w", err)
	}
	if len(blob) < kdfSaltLen {
		return "", errors.New("secret.enc corrupto o incompleto (falta la sal)")
	}

	salt := blob[:kdfSaltLen]
	resto := blob[kdfSaltLen:]

	block, err := aes.NewCipher(derivarLlave(passphrase, salt))
	if err != nil {
		return "", err
	}
	gcm, err := cipher.NewGCM(block)
	if err != nil {
		return "", err
	}

	nonceSize := gcm.NonceSize()
	if len(resto) < nonceSize {
		return "", errors.New("secret.enc corrupto o incompleto (falta el nonce)")
	}
	nonce, ciphertext := resto[:nonceSize], resto[nonceSize:]

	plaintext, err := gcm.Open(nil, nonce, ciphertext, nil)
	if err != nil {
		return "", fmt.Errorf("passphrase incorrecta o secret.enc corrupto: %w", err)
	}
	return string(plaintext), nil
}

// leerLinea imprime prompt y lee una línea de r -- r se comparte entre
// varias llamadas seguidas (ver modoEncriptarSecreto) porque un
// bufio.Reader nuevo en cada llamada puede tragarse de más del buffer
// subyacente y perder las líneas siguientes ya "leídas" pero no
// consumidas por el llamador anterior.
func leerLinea(r *bufio.Reader, prompt string) string {
	fmt.Print(prompt)
	linea, _ := r.ReadString('\n')
	return strings.TrimSpace(linea)
}

func leerPassphrase(prompt string) string {
	return leerLinea(bufio.NewReader(stdinLector), prompt)
}

// modoEncriptarSecreto es el modo "-encrypt": se corre A MANO en la HP
// (equipo de confianza), NUNCA en el equipo ajeno donde vive la USB.
// Produce secret.enc, que es lo único que se copia a la USB junto al
// binario del agente -- el tema en texto plano no debe viajar con ella.
func modoEncriptarSecreto() {
	fmt.Println("=== Cifrar el tema de ntfy.sh para la USB (correr en la HP, no en la USB) ===")

	r := bufio.NewReader(stdinLector)
	topic := leerLinea(r, "Tema de ntfy.sh a cifrar: ")
	if topic == "" {
		fmt.Println("❌ Tema vacío, nada que cifrar")
		return
	}

	pass1 := leerLinea(r, "🔑 Elige una passphrase para proteger el tema en la USB: ")
	pass2 := leerLinea(r, "🔑 Repite la passphrase: ")
	if pass1 == "" || pass1 != pass2 {
		fmt.Println("❌ Las passphrases no coinciden o están vacías -- nada se escribió")
		return
	}

	blob, err := encryptTopic(topic, pass1)
	if err != nil {
		fmt.Printf("❌ Error cifrando: %v\n", err)
		return
	}

	if err := escribirSecretFile(blob); err != nil {
		fmt.Printf("❌ Error escribiendo %s: %v\n", secretFile, err)
		return
	}

	fmt.Printf("✅ %s creado en el directorio actual.\n", secretFile)
	fmt.Println("   Copia SOLO ese archivo (+ el binario del agente) a la USB.")
	fmt.Println("   No dejes HERMES_NTFY_TOPIC en un .env sobre la USB si usas este modo.")
}
