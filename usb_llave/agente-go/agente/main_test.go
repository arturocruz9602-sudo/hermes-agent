package main

import "testing"

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
