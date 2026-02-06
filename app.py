"""
Frontend de Streamlit para Demo de Cumplimiento de Contratos
"""

import asyncio
import base64
import json
import logging
from pathlib import Path
from queue import Queue

import pandas as pd
import streamlit as st

from models import File
from workflow import Demo

st.set_page_config(
    page_title="Cumplimiento de Contratos",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================================
# CSS PERSONALIZADO - ESTILO ENTERPRISE
# ============================================================================

st.markdown(
    """
    <style>
    /* Fondo y estilos globales */
    .main {
        background: #f8fafc;
    }

    /* Tarjetas con sombra */
    .card {
        background: white;
        padding: 2rem;
        border-radius: 8px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        margin-bottom: 1.5rem;
    }

    /* Título principal */
    .main-title {
        font-size: 2.2rem;
        font-weight: 600;
        color: #1e293b;
        text-align: center;
        margin-bottom: 0.5rem;
    }

    .subtitle {
        text-align: center;
        color: #64748b;
        font-size: 1rem;
        margin-bottom: 2rem;
        font-weight: 400;
    }

    /* Botón personalizado */
    .stButton > button {
        width: 100%;
        height: 3.5rem;
        font-size: 1rem;
        font-weight: 600;
        border-radius: 6px;
        background: #2563eb;
        color: white;
        border: none;
        transition: background 0.2s ease;
    }

    .stButton > button:hover {
        background: #1d4ed8;
    }

    /* Métricas personalizadas */
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 6px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        text-align: center;
    }

    .metric-value {
        font-size: 2rem;
        font-weight: 600;
        color: #1e293b;
    }

    .metric-label {
        font-size: 0.875rem;
        color: #64748b;
        margin-top: 0.5rem;
        font-weight: 500;
    }

    /* Tabla estilizada */
    .dataframe {
        font-size: 0.95rem;
    }

    /* Estado aprobado */
    .status-approved {
        background-color: #10b981 !important;
        color: white !important;
        padding: 0.5rem 1rem;
        border-radius: 6px;
        font-weight: 600;
    }

    /* Estado rechazado */
    .status-rejected {
        background-color: #ef4444 !important;
        color: white !important;
        padding: 0.5rem 1rem;
        border-radius: 6px;
        font-weight: 600;
    }

    /* Estado justificado */
    .status-justified {
        background-color: #f59e0b !important;
        color: white !important;
        padding: 0.5rem 1rem;
        border-radius: 6px;
        font-weight: 600;
    }

    /* Sidebar */
    .css-1d391kg {
        background-color: #f8fafc;
    }

    /* PDF viewer container */
    .pdf-container {
        background: white;
        padding: 1rem;
        border-radius: 6px;
        margin-bottom: 1rem;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        border: 1px solid #e2e8f0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================


class StreamlitLogHandler(logging.Handler):
    """Handler that captures logs for Streamlit display."""

    def __init__(self, log_queue: Queue):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record):
        try:
            msg = self.format(record)
            self.log_queue.put(msg)
        except Exception:
            self.handleError(record)


def parse_log_for_status(log_message: str) -> tuple[str, str] | None:
    """Parse log message to extract step status."""
    msg_lower = log_message.lower()

    if "parse_started" in msg_lower or "fetching_documents" in msg_lower:
        if "poliza" in msg_lower:
            return ("📄 Analizando póliza...", "info")
        elif "reporte" in msg_lower:
            return ("📋 Analizando reporte...", "info")
    elif "documents_parsed" in msg_lower:
        if "poliza" in msg_lower:
            return ("✅ Póliza parseada", "success")
        elif "reporte" in msg_lower:
            return ("✅ Reporte parseado", "success")
    elif "parse_completed" in msg_lower:
        return ("✅ Documento procesado", "success")
    elif "extract_poliza_started" in msg_lower:
        return ("🔍 Extrayendo reglas de la póliza...", "info")
    elif "extract_poliza_completed" in msg_lower:
        return ("✅ Reglas extraídas exitosamente", "success")
    elif "validate_reporte_completed" in msg_lower:
        return ("✅ Validación completada", "success")
    elif "end_step" in msg_lower:
        return ("✅ Proceso finalizado", "success")
    return None


def get_pdf_download_link(file_path: str, display_name: str) -> str:
    """Genera un link de descarga para un PDF."""
    with open(file_path, "rb") as f:
        pdf_bytes = f.read()
        b64 = base64.b64encode(pdf_bytes).decode()
        href = f'<a href="data:application/pdf;base64,{b64}" download="{display_name}" style="text-decoration: none; color: #2563eb; font-weight: 500;">Descargar {display_name}</a>'
        return href


def display_pdf_viewer(file_path: str, display_name: str):
    """Muestra un visualizador de PDF básico."""
    st.markdown(f"**{display_name}**")

    with open(file_path, "rb") as f:
        base64_pdf = base64.b64encode(f.read()).decode("utf-8")

    # Embed PDF con altura ajustable
    pdf_display = f"""
        <div class="pdf-container">
            <iframe
                src="data:application/pdf;base64,{base64_pdf}"
                width="100%"
                height="400"
                type="application/pdf"
                style="border: none; border-radius: 8px;">
            </iframe>
        </div>
    """
    st.markdown(pdf_display, unsafe_allow_html=True)

    # Link de descarga
    st.markdown(get_pdf_download_link(file_path, display_name), unsafe_allow_html=True)


def style_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Aplica estilos al DataFrame según el estado."""

    def color_decision(val):
        if "APROBADO" in val.upper():
            return "background-color: #10b981; color: white; font-weight: 600; border-radius: 6px; padding: 0.5rem;"
        elif "RECHAZADO" in val.upper():
            return "background-color: #ef4444; color: white; font-weight: 600; border-radius: 6px; padding: 0.5rem;"
        elif "JUSTIFICADO" in val.upper():
            return "background-color: #f59e0b; color: white; font-weight: 600; border-radius: 6px; padding: 0.5rem;"
        return ""

    styled = df.style.map(color_decision, subset=["Estado"])
    return styled


async def run_workflow(log_queue: Queue | None = None) -> dict:
    """Ejecuta el workflow de validación de pólizas."""
    # Setup logging if queue provided
    handlers = []
    if log_queue:
        # Capture logs from all relevant loggers
        logger_names = [
            "workflow",
            "steps.document_parse.parse",
            "steps.extract_rules",
            "steps.validate_reporte",
        ]

        for logger_name in logger_names:
            logger = logging.getLogger(logger_name)
            handler = StreamlitLogHandler(log_queue)
            handler.setFormatter(logging.Formatter("%(message)s"))
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
            handlers.append((logger, handler))

    try:
        workflow = Demo()

        # Archivos de entrada (paths relativos)
        poliza_file = File(
            path="data/Poliza.pdf",
            name="Poliza.pdf",
            is_poliza=True,
        )
        reporte_file = File(
            path="data/Reporte.pdf",
            name="Reporte.pdf",
            is_poliza=False,
        )

        result = await workflow.run(files=[poliza_file, reporte_file])
        return result
    finally:
        if log_queue:
            for logger, handler in handlers:
                logger.removeHandler(handler)


# ============================================================================
# HEADER
# ============================================================================

st.markdown(
    '<div class="main-title">Sistema de Cumplimiento de Contratos</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="subtitle">Validación Automatizada de Conformidad Contractual</div>',
    unsafe_allow_html=True,
)

# ============================================================================
# SIDEBAR - DOCUMENTOS
# ============================================================================

with st.sidebar:
    st.header("Documentos")

    # Rutas relativas a los documentos
    poliza_path = Path("data/Poliza.pdf")
    reporte_path = Path("data/Reporte.pdf")

    if poliza_path.exists():
        st.markdown("---")
        display_pdf_viewer(str(poliza_path), "Póliza")
    else:
        st.info(f"Documento de póliza: {poliza_path}")

    st.markdown("---")

    if reporte_path.exists():
        display_pdf_viewer(str(reporte_path), "Reporte")
    else:
        st.info(f"Documento de reporte: {reporte_path}")

    st.markdown("---")
    st.markdown(
        """
        <div style="text-align: center; color: #94a3b8; font-size: 0.8rem; margin-top: 2rem;">
        Sistema de Cumplimiento de Contratos v1.0<br/>
        <small>© 2026</small>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ============================================================================
# BOTÓN DE EJECUCIÓN
# ============================================================================

st.markdown("---")

if st.button("EJECUTAR VALIDACIÓN", type="primary", width="stretch"):
    try:
        with st.status("Procesando documentos...", expanded=True) as status:
            # Define all steps upfront
            steps = {
                "parse_poliza": {
                    "name": "Analizar Póliza",
                    "status": "pending",
                    "container": st.empty(),
                },
                "parse_reporte": {
                    "name": "Analizar Reporte",
                    "status": "pending",
                    "container": st.empty(),
                },
                "extract_rules": {
                    "name": "Extraer Reglas de Póliza",
                    "status": "pending",
                    "container": st.empty(),
                },
                "validate": {
                    "name": "Validar Items contra Reglas",
                    "status": "pending",
                    "container": st.empty(),
                },
                "finalize": {
                    "name": "Finalizar Proceso",
                    "status": "pending",
                    "container": st.empty(),
                },
            }

            def update_step_display():
                """Update all step displays based on their current status."""
                for step_key, step_info in steps.items():
                    status_icon = {
                        "pending": "⏳",
                        "running": "🔄",
                        "completed": "✅",
                    }.get(step_info["status"], "⏳")
                    step_info["container"].write(f"{status_icon} {step_info['name']}")

            # Display initial state (all pending)
            update_step_display()

            # Create log queue
            log_queue = Queue()

            # Run workflow in thread
            import threading
            import time

            result_container = {"result": None, "error": None}

            def run_async_workflow():
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    result_container["result"] = loop.run_until_complete(
                        run_workflow(log_queue=log_queue)
                    )
                except Exception as e:
                    result_container["error"] = e
                finally:
                    loop.close()

            # Start workflow
            thread = threading.Thread(target=run_async_workflow)
            thread.start()

            # Update progress based on logs
            while thread.is_alive():
                while not log_queue.empty():
                    try:
                        log_msg = log_queue.get_nowait()
                        msg_lower = log_msg.lower()

                        # Update step status based on log messages
                        if (
                            "parse_started" in msg_lower
                            or "fetching_documents" in msg_lower
                        ):
                            if "poliza" in msg_lower:
                                steps["parse_poliza"]["status"] = "running"
                            elif "reporte" in msg_lower:
                                steps["parse_reporte"]["status"] = "running"
                            update_step_display()

                        elif (
                            "documents_parsed" in msg_lower
                            or "parse_completed" in msg_lower
                        ):
                            if "poliza" in msg_lower:
                                steps["parse_poliza"]["status"] = "completed"
                            elif "reporte" in msg_lower:
                                steps["parse_reporte"]["status"] = "completed"
                            update_step_display()

                        elif "extract_poliza_started" in msg_lower:
                            steps["extract_rules"]["status"] = "running"
                            update_step_display()

                        elif "extract_poliza_completed" in msg_lower:
                            steps["extract_rules"]["status"] = "completed"
                            update_step_display()

                        elif "validate_reporte_completed" in msg_lower:
                            steps["validate"]["status"] = "completed"
                            update_step_display()

                        elif "end_step" in msg_lower:
                            steps["finalize"]["status"] = "completed"
                            update_step_display()

                    except Exception:
                        break
                time.sleep(0.2)

            # Process remaining logs
            for _ in range(10):
                while not log_queue.empty():
                    try:
                        log_msg = log_queue.get_nowait()
                        msg_lower = log_msg.lower()

                        if (
                            "documents_parsed" in msg_lower
                            or "parse_completed" in msg_lower
                        ):
                            if "poliza" in msg_lower:
                                steps["parse_poliza"]["status"] = "completed"
                            elif "reporte" in msg_lower:
                                steps["parse_reporte"]["status"] = "completed"
                        elif "extract_poliza_completed" in msg_lower:
                            steps["extract_rules"]["status"] = "completed"
                        elif "validate_reporte_completed" in msg_lower:
                            steps["validate"]["status"] = "completed"
                        elif "end_step" in msg_lower:
                            steps["finalize"]["status"] = "completed"

                        update_step_display()
                    except Exception:
                        break
                time.sleep(0.1)

            thread.join()

            # Mark all as complete
            for step in steps.values():
                if step["status"] != "completed":
                    step["status"] = "completed"
            update_step_display()

            # Check for errors
            if result_container["error"]:
                raise result_container["error"]

            st.session_state["result"] = result_container["result"]
            status.update(
                label="✅ Validación completada", state="complete", expanded=False
            )

        st.success("**Proceso completado exitosamente**")
        st.rerun()
    except Exception as e:
        st.error(f"**Error:** {str(e)}")
        st.exception(e)

# ============================================================================
# VISUALIZACIÓN DE RESULTADOS
# ============================================================================

if "result" in st.session_state:
    result = st.session_state["result"]

    st.markdown("---")
    st.markdown("## Resultados de la Validación")

    # Extraer datos
    validated_report = result.get("validated_reporte")
    extracted_rules = result.get("extracted_rules")

    if validated_report and "items" in validated_report:
        items = validated_report["items"]
        total_approved = validated_report.get("total_aprobado", 0)

        # Calcular métricas
        total_amount = sum(item.get("costo", 0) for item in items)
        total_rejected = sum(
            item.get("costo", 0)
            for item in items
            if "RECHAZADO" in item.get("decision", "").upper()
        )
        num_items = len(items)
        num_approved = sum(
            1 for item in items if "APROBADO" in item.get("decision", "").upper()
        )
        num_rejected = sum(
            1 for item in items if "RECHAZADO" in item.get("decision", "").upper()
        )
        num_justified = sum(
            1 for item in items if "JUSTIFICADO" in item.get("decision", "").upper()
        )

        # ====================================================================
        # MÉTRICAS PRINCIPALES
        # ====================================================================

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.markdown(
                f"""
                <div class="metric-card" style="border-left: 5px solid #3b82f6;">
                    <div class="metric-value">${total_amount:,.2f}</div>
                    <div class="metric-label">Total Evaluado</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with col2:
            st.markdown(
                f"""
                <div class="metric-card" style="border-left: 5px solid #10b981;">
                    <div class="metric-value" style="color: #10b981;">${total_approved:,.2f}</div>
                    <div class="metric-label">Total Conforme</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with col3:
            st.markdown(
                f"""
                <div class="metric-card" style="border-left: 5px solid #ef4444;">
                    <div class="metric-value" style="color: #ef4444;">${total_rejected:,.2f}</div>
                    <div class="metric-label">Total No Conforme</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with col4:
            approval_rate = (
                (total_approved / total_amount * 100) if total_amount > 0 else 0
            )
            st.markdown(
                f"""
                <div class="metric-card" style="border-left: 5px solid #8b5cf6;">
                    <div class="metric-value" style="color: #8b5cf6;">{approval_rate:.1f}%</div>
                    <div class="metric-label">Tasa de Conformidad</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("<br>", unsafe_allow_html=True)

        # ====================================================================
        # TABS: VISIÓN GENERAL + DETALLE JSON
        # ====================================================================

        tab1, tab2, tab3 = st.tabs(["Resumen", "Detalle JSON", "Reglas Aplicadas"])

        with tab1:
            st.markdown("### Items Validados")

            # Crear DataFrame
            df = pd.DataFrame(items)
            df = df.rename(
                columns={
                    "item": "Item",
                    "costo": "Monto",
                    "decision": "Estado",
                    "explicacion": "Detalle",
                }
            )

            # Formatear columna de monto
            if "Monto" in df.columns:
                df["Monto"] = df["Monto"].apply(lambda x: f"${x:,.2f}")

            # Mostrar tabla estilizada
            st.dataframe(
                style_dataframe(df),
                width="stretch",
                height=400,
            )

            # Resumen de decisiones
            st.markdown("### Resumen de Estados")

            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric(
                    "Conformes",
                    num_approved,
                    f"{num_approved / num_items * 100:.0f}%",
                )

            with col2:
                st.metric(
                    "No Conformes",
                    num_rejected,
                    f"{num_rejected / num_items * 100:.0f}%",
                )

            with col3:
                st.metric(
                    "Con Justificación",
                    num_justified,
                    f"{num_justified / num_items * 100:.0f}%",
                )

        with tab2:
            st.markdown("### Detalle Completo")
            st.json(result)

            # Botón para descargar JSON
            json_str = json.dumps(result, indent=2, default=str)
            st.download_button(
                label="Descargar JSON",
                data=json_str,
                file_name="resultado_validacion.json",
                mime="application/json",
            )

        with tab3:
            st.markdown("### Reglas del Contrato")

            if extracted_rules:
                key_rules = extracted_rules.get("reglas_clave", [])
                deductible = extracted_rules.get("deducible", 0)

                if deductible:
                    st.markdown(f"**Deducible:** {deductible * 100:.1f}%")

                st.markdown("**Reglas Clave:**")
                for i, rule in enumerate(key_rules, 1):
                    st.markdown(f"{i}. {rule}")
            else:
                st.warning("No se encontraron reglas extraídas.")

    else:
        st.warning("No se encontraron items validados en el resultado.")

else:
    # Mensaje inicial antes de ejecutar
    st.info("Haz clic en el botón para iniciar el proceso de validación.")

    st.markdown("---")

    # Información del sistema
    st.markdown("### Proceso de Validación")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(
            """
            **Análisis de Documentos**
            - Extracción de contenido
            - Identificación de reglas y restricciones
            - Validación de requisitos
            """
        )

    with col2:
        st.markdown(
            """
            **Validación de Conformidad**
            - Análisis de cumplimiento
            - Aplicación de reglas contractuales
            - Generación de decisiones
            """
        )
