package main

import (
	"os"
	"testing"
)

// La lista negra es el único candado real antes de proponerle un comando
// a Arturo por Telegram -- se prueba igual de a fondo que cualquier otra
// pieza de seguridad del proyecto (mismo criterio que hermes-guard.sh).

func TestEvaluarComandoBloqueaPeligrosos(t *testing.T) {
	casos := []string{
		"rm -rf /",
		"rm -rf ~",
		"sudo rm -rf /home",
		"mkfs.ext4 /dev/sda1",
		"dd if=/dev/zero of=/dev/sda",
		":(){ :|:& };:",
		"chmod -R 777 /",
		"echo hola > /dev/sda",
		"shutdown -h now",
		"reboot",
		"poweroff",
		`del /s /q c:\`,
		"format c:",
		"net user hacker /add",
		"passwd root",
	}
	for _, cmd := range casos {
		permitido, motivo := evaluarComando(cmd)
		if permitido {
			t.Errorf("evaluarComando(%q) = permitido, se esperaba bloqueado", cmd)
		}
		if motivo == "" {
			t.Errorf("evaluarComando(%q) bloqueó sin dar motivo", cmd)
		}
	}
}

func TestEvaluarComandoPermiteComandosNormales(t *testing.T) {
	casos := []string{
		"ls -la",
		"echo hola",
		"cat archivo.txt",
		"ipconfig",
		"df -h",
		"whoami",
		"ping -c 4 google.com",
	}
	for _, cmd := range casos {
		permitido, motivo := evaluarComando(cmd)
		if !permitido {
			t.Errorf("evaluarComando(%q) = bloqueado (%s), se esperaba permitido", cmd, motivo)
		}
	}
}

func TestEvaluarComandoNoSensibleAMayusculas(t *testing.T) {
	// Un atacante (o un descuido) no debe poder saltarse la lista negra
	// solo cambiando mayúsculas/minúsculas.
	permitido, _ := evaluarComando("RM -RF /")
	if permitido {
		t.Error("evaluarComando(\"RM -RF /\") = permitido -- la lista negra debe ser insensible a mayúsculas")
	}
}

func TestResolverAliasSinCoincidencias(t *testing.T) {
	dir := t.TempDir()
	oldWd, _ := os.Getwd()
	defer os.Chdir(oldWd)
	os.Chdir(dir)
	if err := writeAll(map[string]Dispositivo{}); err != nil {
		t.Fatalf("no pude preparar dispositivos.json de prueba: %v", err)
	}

	_, err := resolverAlias("nada-existe")
	if err == nil {
		t.Error("resolverAlias con dispositivos.json vacío debería fallar, no encontrar nada")
	}
}

func TestResolverAliasAmbiguoFalla(t *testing.T) {
	dir := t.TempDir()
	oldWd, _ := os.Getwd()
	defer os.Chdir(oldWd)
	os.Chdir(dir)
	dispositivos := map[string]Dispositivo{
		"ALMENDRA-abc123": {DeviceID: "ALMENDRA-abc123", OS: "windows"},
		"ALMENDRA-def456": {DeviceID: "ALMENDRA-def456", OS: "windows"},
	}
	if err := writeAll(dispositivos); err != nil {
		t.Fatalf("no pude preparar dispositivos.json de prueba: %v", err)
	}

	_, err := resolverAlias("almendra")
	if err == nil {
		t.Error("resolverAlias con 2 coincidencias debería fallar (ambiguo), no adivinar cuál")
	}
}

func TestResolverAliasUnicaCoincidenciaFunciona(t *testing.T) {
	dir := t.TempDir()
	oldWd, _ := os.Getwd()
	defer os.Chdir(oldWd)
	os.Chdir(dir)
	dispositivos := map[string]Dispositivo{
		"ALMENDRA-abc123":                         {DeviceID: "ALMENDRA-abc123", OS: "windows"},
		"arturo-HP-Laptop-14-ck0xxx-753e5d759768": {DeviceID: "arturo-HP-Laptop-14-ck0xxx-753e5d759768", OS: "linux"},
	}
	if err := writeAll(dispositivos); err != nil {
		t.Fatalf("no pude preparar dispositivos.json de prueba: %v", err)
	}

	id, err := resolverAlias("almendra")
	if err != nil {
		t.Fatalf("resolverAlias(\"almendra\") falló: %v", err)
	}
	if id != "ALMENDRA-abc123" {
		t.Errorf("resolverAlias(\"almendra\") = %q, se esperaba ALMENDRA-abc123", id)
	}
}

func TestMarcarDesconectadoActualizaDispositivo(t *testing.T) {
	dir := t.TempDir()
	oldWd, _ := os.Getwd()
	defer os.Chdir(oldWd)
	os.Chdir(dir)

	dispositivos := map[string]Dispositivo{
		"ALMENDRA-abc123": {DeviceID: "ALMENDRA-abc123", OS: "windows", Connected: true},
	}
	if err := writeAll(dispositivos); err != nil {
		t.Fatalf("no pude preparar dispositivos.json de prueba: %v", err)
	}

	if err := marcarDesconectado("ALMENDRA-abc123"); err != nil {
		t.Fatalf("marcarDesconectado() falló: %v", err)
	}

	leidos, err := leerTodosLosDispositivos()
	if err != nil {
		t.Fatalf("no pude releer dispositivos.json: %v", err)
	}
	d := leidos["ALMENDRA-abc123"]
	if d.Connected {
		t.Error("Connected debería quedar en false tras marcarDesconectado()")
	}
	if d.DisconnectedAt == "" {
		t.Error("DisconnectedAt debería quedar poblado tras marcarDesconectado()")
	}
}

func TestMarcarDesconectadoDispositivoNoRegistradoFalla(t *testing.T) {
	dir := t.TempDir()
	oldWd, _ := os.Getwd()
	defer os.Chdir(oldWd)
	os.Chdir(dir)

	if err := writeAll(map[string]Dispositivo{}); err != nil {
		t.Fatalf("no pude preparar dispositivos.json de prueba: %v", err)
	}

	if err := marcarDesconectado("nunca-existio"); err == nil {
		t.Error("marcarDesconectado() de un dispositivo no registrado debería fallar, no inventar el registro")
	}
}

func TestParsearComandoDeTestSinAliasVaALaHP(t *testing.T) {
	deviceID, comando, aviso := parsearComandoDeTest("ipconfig")
	if deviceID != deviceIDLocalHP {
		t.Errorf("sin alias debería ir a la HP por default, llegó a %q", deviceID)
	}
	if comando != "ipconfig" {
		t.Errorf("comando = %q, se esperaba ipconfig", comando)
	}
	if aviso != "" {
		t.Errorf("no debería haber aviso cuando no hay alias, llegó: %q", aviso)
	}
}

func TestComputeDeviceIDLocalEsEstable(t *testing.T) {
	// deviceIDLocalHP ya no es un string hardcodeado -- si el cálculo
	// cambiara entre llamadas, el "default a la HP" se rompería igual
	// que se rompía antes con un machine-id distinto al literal viejo.
	id1 := computeDeviceIDLocal()
	id2 := computeDeviceIDLocal()
	if id1 != id2 {
		t.Errorf("computeDeviceIDLocal() no es estable: %q != %q", id1, id2)
	}
	if id1 == "" {
		t.Error("computeDeviceIDLocal() devolvió cadena vacía")
	}
}

func TestRequierePrivilegiosElevadosDetectaSudo(t *testing.T) {
	casos := map[string]bool{
		"sudo apt update":       true,
		"ls -la":                false,
		"runas /user:admin cmd": true,
		"doas pkg install x":    true,
	}
	for cmd, esperado := range casos {
		if got := requierePrivilegiosElevados(cmd); got != esperado {
			t.Errorf("requierePrivilegiosElevados(%q) = %v, se esperaba %v", cmd, got, esperado)
		}
	}
}
