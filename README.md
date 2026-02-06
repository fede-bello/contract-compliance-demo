# Sistema de Cumplimiento de Contratos

Sistema automatizado de validación de pólizas de seguro usando LLMs. Analiza documentos PDF y valida ítems reportados contra las reglas de la póliza.

## 📋 Requisitos

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)
- Variables de entorno:
  - `OPENAI_API_KEY`
  - `ANTHROPIC_API_KEY`
  - `LLAMA_CLOUD_API_KEY`

## 🚀 Instalación

```bash
# 1. Instalar uv (si no lo tienes)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Clonar y entrar al proyecto
git clone <repository-url>
cd contract-compliance-demo

# 3. Crear archivo .env con tus API keys
echo "OPENAI_API_KEY=sk-..." >> .env
echo "ANTHROPIC_API_KEY=sk-ant-..." >> .env
echo "LLAMA_CLOUD_API_KEY=llx-..." >> .env

# 4. Instalar dependencias
uv sync
```

## 📂 Archivos requeridos

Coloca tus PDFs en `data/`:

```
data/
├── Poliza.pdf     # Documento de la póliza
└── Reporte.pdf    # Reporte de daños
```

## 💻 Uso

**Interfaz web (recomendado):**
```bash
./run_streamlit.sh
```

**Ejecutar workflow directamente:**
```bash
uv run python workflow.py
```

Generará `reporte_final.json` con los resultados.

## 📊 Flujo

1. **Parseo**: Analiza ambos PDFs con OCR
2. **Extracción**: Extrae reglas y restricciones de la póliza
3. **Validación**: Valida cada ítem del reporte contra las reglas
4. **Decisión**: Aprueba, rechaza o justifica cada ítem

## 🏗️ Estructura

```
├── app.py              # Interfaz Streamlit
├── workflow.py         # Workflow principal
├── models.py           # Modelos de datos
├── steps/              # Pasos del workflow
└── utils/              # Utilidades
```

## 🔧 Modelos LLM

- **Claude Sonnet 4.5**: Extracción y validación
- **OpenAI GPT**: Embeddings
- **LlamaCloud**: Parsing de PDFs

Modifica en `utils/llm.py` si necesitas otros modelos.
