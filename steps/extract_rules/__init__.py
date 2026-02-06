from llama_index.core.prompts import PromptTemplate
from utils.llm import get_llm

from models import ExtractedRules, ParseResult

PROMPT_EXTRACCION = """
Eres un experto Suscriptor de Seguros (Underwriter AI).
Tu tarea es analizar el texto de esta Póliza de Seguro Automotriz y extraer las reglas operativas clave.

DOCUMENTO (Markdown):
{text}

OBJETIVOS DE EXTRACCIÓN:
1. Deducible: Extrae el porcentaje exacto (ej. 0.05).
2. Reglas Clave: Genera una lista de textos cortos resumiendo las restricciones.
   - Busca explícitamente topes de montos (ej. Pintura).
   - Busca exclusiones claras (ej. Mantenimiento).
   - IMPORTANTE: Busca la cláusula sobre "Daños Ocultos" o "Piezas Estructurales". ¿Qué condición pide para pagarlos? (ej. "Requiere evidencia/nota técnica").

Salida requerida: JSON basado en el esquema ExtractedRules.
"""


async def extract_poliza(parse_result: ParseResult) -> ExtractedRules:
    llm = get_llm(model="claude-sonnet-4-5")
    prompt = PromptTemplate(PROMPT_EXTRACCION)

    return await llm.astructured_predict(
        ExtractedRules,
        prompt,
        text=parse_result.markdown or parse_result.text,
    )
