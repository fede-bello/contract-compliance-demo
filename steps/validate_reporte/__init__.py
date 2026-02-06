from llama_index.core.prompts import PromptTemplate

from models import ExtractedRules, ParseResult, ReporteValidation
from utils.llm import get_llm

PROMPT_VALIDACION = """
Eres un Auditor Financiero Estricto (Claims Auditor).
Concilia la Factura contra las Reglas.

INPUT 1: REGLAS (Contexto):
{reglas_context}

INPUT 2: FACTURA (Markdown):
{factura_text}

INSTRUCCIONES CRÍTICAS DE DECISIÓN:
1. CAMPO 'COSTO': Debes extraer el precio EXACTO que aparece en la factura del taller. NO lo ajustes a la baja. Si la factura dice $5,000, pon 5000.

2. LOGICA DE APROBACIÓN:
   - CASO A (RECHAZO POR PRECIO): Si el costo de la factura es MAYOR al tope de la póliza (ej. Factura $5000 vs Tope $4000), marca decision="RECHAZADO". En la explicación di: "Excede el tope de $4,000".
   - CASO B (DAÑO OCULTO): Si es una pieza estructural nueva (Absorbedor, Alma) y hay nota técnica ("fractura", "daño"), marca decision="JUSTIFICADO_POR_NOTA".
   - CASO C (OK): Si coincide y el precio es menor/igual al tope, marca decision="APROBADO".

3. OBJETIVO VISUAL:
   - Queremos detectar los errores. No seas permisivo. Si se pasan del tope, es RECHAZO.

Salida requerida: JSON basado en el esquema ReporteValidation.
"""


async def validate_reporte(
    parse_result: ParseResult, extracted_rules: ExtractedRules
) -> ReporteValidation:
    llm = get_llm(model="claude-sonnet-4-5")
    prompt = PromptTemplate(PROMPT_VALIDACION)

    reglas_context = f"Deducible: {extracted_rules.deducible}\nReglas:\n" + "\n".join(
        [f"- {r}" for r in extracted_rules.reglas_clave]
    )

    return await llm.astructured_predict(
        ReporteValidation,
        prompt,
        reglas_context=reglas_context,
        factura_text=parse_result.markdown or parse_result.text,
    )
