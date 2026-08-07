package main

import (
	"os"
	"strings"
	"testing"
)

func TestEncryptDecryptTopicRoundTrip(t *testing.T) {
	blob, err := encryptTopic("mi-tema-secreto-de-ntfy", "passphrase-correcta")
	if err != nil {
		t.Fatalf("encryptTopic() falló: %v", err)
	}

	topic, err := decryptTopic(blob, "passphrase-correcta")
	if err != nil {
		t.Fatalf("decryptTopic() falló: %v", err)
	}
	if topic != "mi-tema-secreto-de-ntfy" {
		t.Errorf("decryptTopic() = %q, se esperaba mi-tema-secreto-de-ntfy", topic)
	}
}

func TestDecryptTopicPassphraseIncorrectaFalla(t *testing.T) {
	blob, err := encryptTopic("otro-tema", "passphrase-real")
	if err != nil {
		t.Fatalf("encryptTopic() falló: %v", err)
	}

	_, err = decryptTopic(blob, "passphrase-equivocada")
	if err == nil {
		t.Error("decryptTopic() con passphrase equivocada debería fallar, no devolver basura como si fuera el tema real")
	}
}

func TestDecryptTopicBlobCorruptoFalla(t *testing.T) {
	_, err := decryptTopic("no-es-base64-valido-!!!", "cualquiera")
	if err == nil {
		t.Error("decryptTopic() con un blob corrupto debería fallar")
	}
}

func TestEncryptTopicNoRepiteSaltNiNonce(t *testing.T) {
	// Dos cifrados del mismo tema con la misma passphrase deben verse
	// distintos (sal/nonce aleatorios) -- si no, dos USBs cifradas con el
	// mismo tema y passphrase filtrarían que comparten secreto.
	blob1, err := encryptTopic("tema-repetido", "misma-passphrase")
	if err != nil {
		t.Fatalf("encryptTopic() falló: %v", err)
	}
	blob2, err := encryptTopic("tema-repetido", "misma-passphrase")
	if err != nil {
		t.Fatalf("encryptTopic() falló: %v", err)
	}
	if blob1 == blob2 {
		t.Error("dos cifrados del mismo tema con la misma passphrase no deberían producir el mismo blob")
	}
}

func TestModoEncriptarSecretoEscribeArchivoDescifrable(t *testing.T) {
	dir := t.TempDir()
	oldWd, _ := os.Getwd()
	defer os.Chdir(oldWd)
	os.Chdir(dir)

	entradaOriginal := stdinLector
	defer func() { stdinLector = entradaOriginal }()
	stdinLector = strings.NewReader("tema-de-la-usb\npassphrase123\npassphrase123\n")

	modoEncriptarSecreto()

	data, err := os.ReadFile(secretFile)
	if err != nil {
		t.Fatalf("modoEncriptarSecreto() no escribió %s: %v", secretFile, err)
	}

	topic, err := decryptTopic(string(data), "passphrase123")
	if err != nil {
		t.Fatalf("no pude descifrar el secret.enc generado: %v", err)
	}
	if topic != "tema-de-la-usb" {
		t.Errorf("tema descifrado = %q, se esperaba tema-de-la-usb", topic)
	}
}

func TestModoEncriptarSecretoPassphrasesDistintasNoEscribeArchivo(t *testing.T) {
	dir := t.TempDir()
	oldWd, _ := os.Getwd()
	defer os.Chdir(oldWd)
	os.Chdir(dir)

	entradaOriginal := stdinLector
	defer func() { stdinLector = entradaOriginal }()
	stdinLector = strings.NewReader("tema-de-la-usb\npass-a\npass-b\n")

	modoEncriptarSecreto()

	if _, err := os.Stat(secretFile); err == nil {
		t.Error("con passphrases que no coinciden, no debería haberse escrito secret.enc")
	}
}
