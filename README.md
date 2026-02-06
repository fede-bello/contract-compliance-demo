# Sistema de Validación de Pólizas

Sistema automatizado para validar reportes de daños contra las reglas de una póliza de seguro. Procesa documentos PDF y genera decisiones de aprobación, rechazo o justificación para cada ítem.

## Requisitos

- Python 3.11+
- uv (gestor de paquetes)
- Variables de entorno:
  - `OPENAI_API_KEY`
  - `ANTHROPIC_API_KEY`
  - `LLAMA_CLOUD_API_KEY`

## Instalación

```bash
# 1. Instalar uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Clonar proyecto
git clone <repository-url>
cd contract-compliance-demo

# 3. Crear .env
echo "OPENAI_API_KEY=sk-..." >> .env
echo "ANTHROPIC_API_KEY=sk-ant-..." >> .env
echo "LLAMA_CLOUD_API_KEY=llx-..." >> .env

# 4. Instalar dependencias
uv sync
```

## Archivos de entrada

Coloca los PDFs en `data/`:

```
data/
├── Poliza.pdf     # Documento de la póliza
└── Reporte.pdf    # Reporte de daños
```

## Uso

Interfaz web:

```bash
./run_streamlit.sh
```

O ejecutar directamente:

```bash
uv run python workflow.py
```

Genera `reporte_final.json` con los resultados.

## Flujo de trabajo

1. Parseo de documentos PDF
2. Extracción de reglas de la póliza
3. Validación de ítems del reporte contra las reglas
4. Generación de decisiones por ítem

## Estructura del proyecto

```
├── app.py              Interfaz Streamlit
├── workflow.py         Workflow principal
├── models.py           Modelos de datos
├── steps/              Pasos del workflow
│   ├── document_parse/
│   ├── extract_rules/
│   └── validate_reporte/
└── utils/              Utilidades
    ├── llm.py
    └── logging.py
```

## Control de calidad

```bash
uv run ruff check --fix .    # Linting
uv run ruff format .         # Formateo
pre-commit run --all-files   # Pre-commit hooks
```
