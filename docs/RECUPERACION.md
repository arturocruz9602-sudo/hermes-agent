# Recuperación total de Hermes

Runbook humano (HAS §E13-c) -- los pasos para reconstruir Hermes desde
cero **sin Claude Code disponible**. Piensa en esto como "la HP murió,
tengo una laptop nueva y el disco Seagate, ¿ahora qué".

**Estado real de la automatización (30 jul 2026):** el RESPALDO ya está
automatizado y probado. La RECONSTRUCCIÓN todavía no -- este documento
son los pasos manuales de hoy, no un script que los haga solo. Cuando
`scripts/restaurar_hermes.sh restaurar` exista de verdad, este archivo
se actualiza para reflejarlo (y probablemente se reduzca a "corre este
comando").

## Qué necesitas antes de empezar

1. Una máquina con Ubuntu (o similar) y `git`, `python3.11+`, `rsync`
   instalados.
2. El disco Seagate conectado (`/mnt/seagate/hermes_backups/<fecha>/`
   -- el respaldo más reciente que quieras usar).
3. Acceso al fork de GitHub (`arturocruz9602-sudo/hermes-agent`,
   rama `arturo/prod`).
4. **La passphrase de tu bóveda de credenciales.** Solo tú la sabes --
   nadie más puede completar este paso por ti, a propósito (HAS §E13-a).

## Paso 0 -- generar (o confirmar) un respaldo reciente

Si Hermes todavía está vivo y quieres asegurar un respaldo fresco antes
de que algo le pase:

```bash
cd ~/.hermes/hermes-agent
scripts/restaurar_hermes.sh respaldar --con-credenciales
```

Esto te va a pedir la passphrase dos veces (age cifrando tu `.env`).
Si solo quieres refrescar memoria/skills/systemd sin tocar
credenciales, omite `--con-credenciales` -- copia hacia adelante la
última copia cifrada que ya exista, sin pedir nada.

El resultado queda en `/mnt/seagate/hermes_backups/<timestamp>/` con:
`state.db`, `memoria_semantica.db`, `skills/`, `systemd/`, y
`env.age` (si hubo credenciales).

## Paso 1 -- clonar el código

```bash
git clone git@github.com:arturocruz9602-sudo/hermes-agent.git ~/.hermes/hermes-agent
cd ~/.hermes/hermes-agent
git checkout arturo/prod
```

## Paso 2 -- reconstruir el entorno Python

```bash
./setup-hermes.sh
```

Esto crea el venv y las dependencias. Si falla, revisa `docs/HAS.md`
sección B1 (regla dura: nunca `pip install -U` ni `git pull` sobre
producción sin pasar por Fase 2 -- aquí es una instalación nueva, no
aplica esa regla, pero si algo se ve raro, para y confirma antes de
seguir a mano).

## Paso 3 -- restaurar memoria, skills y timers

Elige el respaldo más reciente de `/mnt/seagate/hermes_backups/`:

```bash
BACKUP=/mnt/seagate/hermes_backups/<timestamp-que-elegiste>
mkdir -p ~/.hermes

# Memoria (state.db, memoria_semantica.db)
cp "$BACKUP/state.db" "$BACKUP/memoria_semantica.db" ~/.hermes/

# Skills
rsync -a "$BACKUP/skills/" ~/.hermes/skills/

# Unidades systemd
mkdir -p ~/.config/systemd/user
cp -r "$BACKUP"/systemd/* ~/.config/systemd/user/
```

**Antes de habilitar los servicios:** revisa `~/.config/systemd/user/
hermes-gateway.service` (y los demás) por rutas absolutas que puedan
apuntar a la HP vieja (ej. un usuario distinto, otra ruta de venv) --
edítalas si no coinciden con la máquina nueva.

```bash
systemctl --user daemon-reload
systemctl --user enable --now hermes-gateway.service litellm.service \
  hermes-watchdog.timer hermes-memoria-index.timer \
  hermes-memoria-reflexion.timer hermes-raw-export.timer \
  hermes-deepseek-balance-check.timer
```

## Paso 4 -- descifrar tus credenciales

```bash
python3 scripts/bovedar_secretos.py descifrar "$BACKUP/env.age" --dest ~/.hermes/.env
```

`age` te va a pedir la passphrase UNA vez (interactiva, en tu terminal
real -- no la escribas en ningún otro lado). Si la passphrase es
incorrecta, falla claro y no suelta nada -- vuelve a intentar.

## Paso 5 -- verificar que de verdad funciona

No des esto por cerrado solo porque los comandos no tronaron:

```bash
systemctl --user status hermes-gateway.service litellm.service
journalctl --user -u hermes-gateway.service -n 50
```

**La prueba real (HAS §E13, verificación E2E):** mándale un mensaje a
Hermes por Telegram y confirma que responde, Y que puede recuperar al
menos un hecho real de tu memoria (pregúntale algo que solo supiera si
la memoria restaurada de verdad cargó). Sin esto, "los comandos
corrieron" no es lo mismo que "Hermes está de vuelta".

## Notas importantes

- **`~/.hermes/boveda/entries.json.enc` (si existe en tu respaldo) es
  OTRO mecanismo**, gestionado por `tools/vault_tool.py` -- credenciales
  que le pediste a Hermes recordar en conversación (contraseñas
  sueltas, etc.), NO tu `.env`. Restaurarlo es tan simple como copiar
  el archivo de vuelta a `~/.hermes/boveda/` -- pero hoy ese directorio
  NO está incluido en el respaldo automatizado de
  `restaurar_hermes.sh` (pendiente, ver `docs/ESTADO.md`).
- Si algo de este runbook ya no coincide con la realidad (rutas,
  nombres de servicios, pasos que ya se automatizaron), es una señal
  de que este documento quedó desactualizado -- corrígelo la próxima
  vez que lo uses o pídele a Claude Code que lo revise contra el código
  real.

## Pendiente antes de que esto cuente como "recuperación total" (HAS §E13)

1. Automatizar los pasos 1-4 en `scripts/restaurar_hermes.sh restaurar`
   (hoy sale con un mensaje explícito de "no implementado" en vez de
   fingir que funciona).
2. **La primera prueba de restauración real, obligatoria** (HAS
   §E13-b): correr todo esto de verdad en una máquina o usuario Linux
   limpio -- NUNCA sobre este equipo en producción. Repetirla cada 3
   meses después. Sin esa prueba, este documento es una teoría, no un
   respaldo verificado.
3. Decidir si `~/.hermes/boveda/` (vault_tool.py) se suma al respaldo
   automatizado, y si vale la pena migrarlo a `age` ahora que ya está
   instalado (nota dejada en `docs/BLOQUES.md`, Bloque 2 paso 3).
