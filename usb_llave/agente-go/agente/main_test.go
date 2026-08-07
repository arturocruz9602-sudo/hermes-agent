package main

import (
	"os"
	"strings"
	"testing"
)

func TestGetDeviceIDEsEstable(t *testing.T) {
	// El device_id debe ser el mismo entre llamadas en la misma máquina --
	// si cambiara cada vez, el gateway vería "dispositivos nuevos" sin fin
	// y nunca podría reconocer una sesión que vuelve a conectar.
	id1 := getDeviceID()
	id2 := getDeviceID()
	if id1 != id2 {
		t.Errorf("getDeviceID() no es estable: %q != %q", id1, id2)
	}
	if id1 == "" {
		t.Error("getDeviceID() devolvió cadena vacía")
	}
}

func TestExtraerUltimoCampo(t *testing.T) {
	salida := "HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Cryptography\n    MachineGuid    REG_SZ    abc-123-def\n"
	got := extraerUltimoCampo(salida)
	if got != "abc-123-def" {
		t.Errorf("extraerUltimoCampo() = %q, se esperaba abc-123-def", got)
	}
}

func TestExtraerIOPlatformUUID(t *testing.T) {
	salida := `+-o IOPlatformExpertDevice
    "IOPlatformUUID" = "12345678-ABCD-1234-ABCD-1234567890AB"
    "board-id" = <"Mac-abc">`
	got, err := extraerIOPlatformUUID(salida)
	if err != nil {
		t.Fatalf("extraerIOPlatformUUID() falló: %v", err)
	}
	if got != "12345678-ABCD-1234-ABCD-1234567890AB" {
		t.Errorf("extraerIOPlatformUUID() = %q, valor inesperado", got)
	}
}

func TestExtraerIOPlatformUUIDSinCoincidenciaFalla(t *testing.T) {
	_, err := extraerIOPlatformUUID("nada de UUID aquí")
	if err == nil {
		t.Error("extraerIOPlatformUUID() debería fallar si no encuentra la línea, no inventar un UUID")
	}
}

func TestCargarTopicPrefiereVariableDeEntorno(t *testing.T) {
	dir := t.TempDir()
	oldWd, _ := os.Getwd()
	defer os.Chdir(oldWd)
	os.Chdir(dir)

	os.Setenv("HERMES_NTFY_TOPIC", "tema-de-env")
	defer os.Unsetenv("HERMES_NTFY_TOPIC")

	// Si intentara leer secret.enc con la variable presente, se colgaría
	// esperando stdin -- no tocar stdinLector aquí es parte de la prueba.
	got := cargarTopic()
	if string(got) != "tema-de-env" {
		t.Errorf("cargarTopic() = %q, se esperaba tema-de-env (variable de entorno)", string(got))
	}
}

func TestCargarTopicCaeASecretEncSinVariable(t *testing.T) {
	dir := t.TempDir()
	oldWd, _ := os.Getwd()
	defer os.Chdir(oldWd)
	os.Chdir(dir)

	os.Unsetenv("HERMES_NTFY_TOPIC")

	blob, err := encryptTopic("tema-cifrado", "clave-usb")
	if err != nil {
		t.Fatalf("encryptTopic() falló: %v", err)
	}
	if err := escribirSecretFile(blob); err != nil {
		t.Fatalf("no pude preparar secret.enc de prueba: %v", err)
	}

	entradaOriginal := stdinLector
	defer func() { stdinLector = entradaOriginal }()
	stdinLector = strings.NewReader("clave-usb\n")

	got := cargarTopic()
	if string(got) != "tema-cifrado" {
		t.Errorf("cargarTopic() = %q, se esperaba tema-cifrado (desde secret.enc)", string(got))
	}
}

func TestCargarTopicSinNadaDevuelveVacio(t *testing.T) {
	dir := t.TempDir()
	oldWd, _ := os.Getwd()
	defer os.Chdir(oldWd)
	os.Chdir(dir)

	os.Unsetenv("HERMES_NTFY_TOPIC")

	got := cargarTopic()
	if got != nil {
		t.Errorf("cargarTopic() sin variable ni secret.enc = %q, se esperaba nil/vacío", string(got))
	}
}

func TestLimpiarBytesSobreescribeConCeros(t *testing.T) {
	b := []byte("secreto")
	limpiarBytes(b)
	for i, v := range b {
		if v != 0 {
			t.Errorf("limpiarBytes() dejó byte[%d]=%d, se esperaba 0", i, v)
		}
	}
}
