# Instalación de Lemoria

## Requisitos

- **Python** >= 3.11 + pip
- **Docker** + **Docker Compose**
- **OpenCode** (opcional, para usar agentes)
- **Obsidian** (opcional, para visualizar vault)

## Instalación rápida (recomendada)

```bash
git clone https://github.com/cristianl0pez-dev/lemoria.git
cd lemoria
chmod +x install.sh
./install.sh
```

Esto instala `lemoria` como **comando global** disponible desde cualquier terminal.

## Instalación paso a paso

### 1. Clonar

```bash
git clone https://github.com/cristianl0pez-dev/lemoria.git
cd lemoria
```

### 2. Configurar entorno

```bash
cp .env.example .env
```

### 3. Iniciar PostgreSQL

```bash
docker compose up -d
# Esperar a que esté healthy:
docker compose exec db pg_isready -U lemoria
```

### 4. Instalar Lemoria globalmente

```bash
pip install --user -e ".[dev]"
```

Asegúrate de que `~/.local/bin` esté en tu `PATH`. Si no:

```bash
echo 'export PATH="$PATH:$HOME/.local/bin"' >> ~/.bashrc  # o ~/.zshrc
```

### 5. Inicializar

```bash
lemoria init
```

### 6. Verificar

```bash
lemoria project list
# → (lista vacía, sin proyectos aún)
```

## Uso

El comando `lemoria` ahora funciona globalmente:

```bash
# Crear proyecto
lemoria project create "mi-proyecto" -d "Descripción"

# Iniciar flujo SDD
lemoria flow start <project-id> "descripción de la idea"

# Conversaciones
lemoria conv create <project-id> -t "Título"
lemoria conv add <conv-id> user "mensaje"

# Agentes
lemoria agent list
```

## Notas

- PostgreSQL debe estar **siempre corriendo** para que Lemoria funcione
- El vault de Obsidian se sincroniza desde PostgreSQL (BD es fuente de verdad)
- `opencode.jsonc` ya tiene los 7 agentes configurados en `agents/`
