# Instalación de Lemoria

## Requisitos

- **Python** >= 3.11
- **Docker** + **Docker Compose** (para PostgreSQL)
- **pip** y **venv**
- **Git**
- **OpenCode** (CLI)
- **Obsidian** (opcional, para visualización del vault)

## Instalación rápida

```bash
chmod +x install.sh
./install.sh
```

Esto ejecutará todo automáticamente: PostgreSQL, dependencias, init y configuración.

## Instalación paso a paso

### 1. Clonar el repositorio

```bash
git clone https://github.com/cristianl0pez-dev/lemoria.git
cd lemoria
```

### 2. Configurar variables de entorno

```bash
cp .env.example .env
```

Edita `.env` si necesitas cambiar credenciales o rutas.

### 3. Iniciar PostgreSQL

```bash
docker compose up -d
```

Espera a que esté saludable:

```bash
docker compose ps
# Debería mostrar "healthy" en el STATUS
```

### 4. Instalar dependencias Python

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### 5. Inicializar Lemoria

```bash
python -m lemoria init
```

Esto crea las tablas en PostgreSQL y el directorio `vault/obsidian/`.

### 6. Verificar instalación

```bash
python -m lemoria project list
# Debería mostrar lista vacía (sin proyectos aún)
```

### 7. Abrir Obsidian (opcional)

Abre Obsidian y selecciona "Abrir carpeta como vault" → `vault/obsidian/`.

## Comandos básicos

```bash
# Crear un proyecto
python -m lemoria project create "mi-proyecto" -d "Descripción"

# Iniciar una conversación
python -m lemoria conv create <project-id> -t "Título"

# Agregar mensaje
python -m lemoria conv add <conv-id> user "contenido del mensaje"

# Iniciar flujo SDD
python -m lemoria flow start <project-id> "descripción de la idea"

# Listar agentes registrados
python -m lemoria agent list
```

## Arquitectura de servicios

```
Sistema local
├── Docker: PostgreSQL (puerto 5432)
├── Python: CLI Lemoria
├── OpenCode: Agentes multi-rol
└── Obsidian: Vault en vault/obsidian/
```

## Notas importantes

- PostgreSQL debe estar corriendo **siempre** para que Lemoria funcione
- El vault de Obsidian se sincroniza desde PostgreSQL (BD es fuente de verdad)
- Los agentes se definen en `agents/` y se cargan vía `opencode.jsonc`
- Usa `.env` para credenciales locales (no se sube a git)
