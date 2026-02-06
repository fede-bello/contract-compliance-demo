import asyncio
import json

from llama_index.core.workflow import Context, StartEvent, StopEvent, Workflow, step

from events import (
    ExtractedPolizaEventCompleted,
    ReporteParsedEventCompleted,
    ReporteValidatedEvent,
    StartParseEvent,
    StartPolizaExtractionEvent,
)
from models import (
    ExtractedRules,
    File,
    ParseResult,
    ReporteValidation,
)
from steps.document_parse import parse_document
from steps.extract_rules import extract_poliza
from steps.validate_reporte import validate_reporte
from utils.logging import get_logger

logger = get_logger(__name__)


class Demo(Workflow):
    @step
    async def start(self, ctx: Context, ev: StartEvent) -> StartParseEvent | None:
        """Dispatch parse step."""
        files: list[File] = ev.files
        for file in files:
            ctx.send_event(StartParseEvent(file=file))

        return None

    @step
    async def parse_step(
        self, ctx: Context, ev: StartParseEvent
    ) -> StartPolizaExtractionEvent | ReporteParsedEventCompleted:
        """Parse contract document using LlamaParse."""
        file: File = ev.file
        logger.info("parse_started | file_path=%s", file.path)

        parse_result: ParseResult = await parse_document(
            [file],
            verbose=True,
            skip_diagonal_text=True,  # Helps ignore watermarks
            merge_tables_across_pages_in_markdown=True,  # Better for table continuity
            parse_mode="parse_page_with_agent",  # Agentic parsing for complex layouts
            check_interval=3,
            outlined_table_extraction=True,
            high_res_ocr=True,
            system_prompt_append="The document must start with a level 1 heading.",
        )
        logger.info(
            "parse_completed | page_count=%s | table_count=%s",
            parse_result.page_count,
            parse_result.table_count,
        )

        if file.is_poliza:
            return StartPolizaExtractionEvent(parse_result=parse_result)
        else:
            return ReporteParsedEventCompleted(parse_result=parse_result)

    @step
    async def extract_poliza_step(
        self, ctx: Context, ev: StartPolizaExtractionEvent
    ) -> ExtractedPolizaEventCompleted:
        """Extract poliza from parse result."""
        parse_result: ParseResult = ev.parse_result
        logger.info(
            "extract_poliza_started | page_count=%s | table_count=%s",
            parse_result.page_count,
            parse_result.table_count,
        )

        extracted_rules: ExtractedRules = await extract_poliza(parse_result)
        await ctx.store.set("extracted_rules", extracted_rules)
        logger.info("extract_poliza_completed | extracted_rules=%s", extracted_rules)

        return ExtractedPolizaEventCompleted(extracted_rules=extracted_rules)

    @step
    async def validate_reporte_step(
        self,
        ctx: Context,
        ev: ReporteParsedEventCompleted | ExtractedPolizaEventCompleted,
    ) -> ReporteValidatedEvent:
        """Validate reporte from parse result."""
        events = ctx.collect_events(
            ev, [ReporteParsedEventCompleted, ExtractedPolizaEventCompleted]
        )
        if events is None:
            return None

        reporte_ev = next(
            e for e in events if isinstance(e, ReporteParsedEventCompleted)
        )
        rules_ev = next(
            e for e in events if isinstance(e, ExtractedPolizaEventCompleted)
        )

        parse_result = reporte_ev.parse_result
        extracted_rules = rules_ev.extracted_rules

        validated_reporte: ReporteValidation = await validate_reporte(
            parse_result, extracted_rules
        )
        await ctx.store.set("validated_reporte", validated_reporte)
        logger.info(
            "validate_reporte_completed | validated_reporte=%s", validated_reporte
        )

        return ReporteValidatedEvent(validated_reporte=validated_reporte)

    @step
    async def end_step(self, ctx: Context, ev: ReporteValidatedEvent) -> StopEvent:
        """End workflow."""
        validated_reporte = await ctx.store.get("validated_reporte")
        extracted_rules = await ctx.store.get("extracted_rules")

        reporte_final = {
            "validated_reporte": (
                validated_reporte.model_dump() if validated_reporte else None
            ),
            "extracted_rules": extracted_rules.model_dump()
            if extracted_rules
            else None,
        }
        logger.info("end_step | reporte_final=%s", reporte_final)

        return StopEvent(result=reporte_final)


async def main():
    workflow = Demo()
    poliza_file = File(
        path="data/Poliza.pdf",
        name="poliza.pdf",
        is_poliza=True,
    )
    reporte_file = File(
        path="data/Reporte.pdf",
        name="reporte.pdf",
        is_poliza=False,
    )
    reporte_final = await workflow.run(files=[poliza_file, reporte_file])
    with open("reporte_final.json", "w") as f:
        json.dump(reporte_final, f, indent=2, default=str)
    print("Workflow completed. Result saved to reporte_final.json")


if __name__ == "__main__":
    asyncio.run(main())
