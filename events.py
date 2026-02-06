from llama_index.core.workflow import Event

from models import (
    ExtractedRules,
    File,
    ParseResult,
    ReporteValidation,
)


class StartParseEvent(Event):
    """Event to trigger document parsing."""

    file: File


class ParseCompletedEvent(Event):
    """Emitted when parsing completes."""

    parse_result: ParseResult


class StartPolizaExtractionEvent(Event):
    """Event to trigger poliza extraction."""

    parse_result: ParseResult


class StartReporteExtractionEvent(Event):
    """Event to trigger reporte extraction."""

    parse_result: ParseResult


class ExtractedPolizaEventCompleted(Event):
    """Emitted when poliza extraction completes."""

    extracted_rules: ExtractedRules


class ReporteParsedEventCompleted(Event):
    """Emitted when reporte parsing completes."""

    parse_result: ParseResult


class ReporteValidatedEvent(Event):
    """Emitted when reporte validation completes."""

    validated_reporte: ReporteValidation
