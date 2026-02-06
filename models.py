from typing import Any

from llama_cloud_services.parse.types import JobResult, Page, PageItem
from pydantic import BaseModel, ConfigDict, Field


class File(BaseModel):
    """File metadata for document processing.

    Encapsulates both the file path and display name to ensure they stay in sync
    throughout the workflow.
    """

    path: str = Field(..., description="Full file path or URI to the document")
    name: str = Field(
        ..., description="Display name or original filename of the document"
    )
    is_poliza: bool


class Heading(BaseModel):
    """Schema for hierarchical heading items."""

    heading: str
    level: int
    subheadings: list["Heading"] = []


class ParseResult(BaseModel):
    """Serializable parse result from LlamaParse."""

    job_id: str
    markdown: str | None = None
    text: str
    pages: list[Page] = []
    page_count: int = 0
    raw_json: dict[str, Any] | None = None

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @property
    def all_tables(self) -> list[tuple[int, PageItem]]:
        """Get all tables across all pages as (page_num, item) tuples."""
        tables = []
        for page in self.pages:
            for item in page.items:
                if item.type == "table":
                    tables.append((page.page, item))
        return tables

    @property
    def table_count(self) -> int:
        """Total number of tables detected."""
        return len(self.all_tables)

    @property
    def page_numbers(self) -> list[int]:
        """Get all page numbers in order."""
        return sorted([p.page for p in self.pages])

    @property
    def headings(self) -> list[Heading]:
        """Get all headings in a hierarchical list structure."""
        root: list[Heading] = []
        stack: list[tuple[int, list[Heading]]] = [(0, root)]

        for page in self.pages:
            for item in page.items:
                if item.type == "heading":
                    level = getattr(item, "lvl", 1)
                    text = getattr(item, "value", getattr(item, "text", ""))

                    while stack[-1][0] >= level:
                        stack.pop()

                    new_item = Heading(heading=text, level=level, subheadings=[])
                    stack[-1][1].append(new_item)

                    stack.append((level, new_item.subheadings))

        return root

    @property
    def headings_text(self) -> str:
        """Get all headings as a formatted hierarchical string."""

        def format_headings(headings: list[Heading], depth: int = 0) -> list[str]:
            lines = []
            for h in headings:
                lines.append("  " * depth + f"- {h.heading}")
                if h.subheadings:
                    lines.extend(format_headings(h.subheadings, depth + 1))
            return lines

        return "\n".join(format_headings(self.headings))

    def build_result_from_pages(self, filtered_pages: list[Page]) -> "ParseResult":
        """Helper to create a new ParseResult from a list of filtered pages."""
        # Rebuild global text and markdown
        texts = [p.text for p in filtered_pages if p.text]
        markdowns = [p.md for p in filtered_pages if p.md]

        filtered_raw_json = None
        if self.raw_json and "pages" in self.raw_json:
            filtered_raw_json = {
                **self.raw_json,
                "pages": [p.dict() for p in filtered_pages],
            }

        return ParseResult(
            job_id=self.job_id,
            markdown="\n\n".join(markdowns) if markdowns else None,
            text="\n\n".join(texts),
            pages=filtered_pages,
            page_count=len(filtered_pages),
            raw_json=filtered_raw_json,
        )

    def filter_by_pages(self, selected_pages: list[int]) -> "ParseResult":
        """Create a new ParseResult containing only the selected pages."""
        if not selected_pages:
            return self

        filtered_pages = [p for p in self.pages if p.page in selected_pages]
        return self.build_result_from_pages(filtered_pages)

    def get_section(self, section_path: list[str] | str) -> "ParseResult | None":
        """Extract a specific section from the document by its heading path.

        Args:
            section_path: A single heading name (str) or a list of heading names
                         representing the hierarchical path from root to the target section.

        Returns:
            A new ParseResult instance containing only the content of the selected section,
            including its subheadings, or None if the section path is not found.
        """
        target_path = [section_path] if isinstance(section_path, str) else section_path
        if not target_path:
            return None

        collecting = False
        section_lvl: int | None = None
        stack: list[tuple[int, str]] = []
        collected_data: list[tuple[Page, list[PageItem]]] = []

        for page in self.pages:
            current_page_items: list[PageItem] = []
            for item in page.items:
                if item.type == "heading":
                    lvl = getattr(item, "lvl", 1)
                    txt = getattr(item, "value", getattr(item, "text", ""))

                    while stack and stack[-1][0] >= lvl:
                        stack.pop()
                    stack.append((lvl, txt))

                    if not collecting:
                        if [h[1] for h in stack] == target_path:
                            collecting, section_lvl = True, lvl
                    elif section_lvl is not None and lvl <= section_lvl:
                        collecting = False
                        break

                if collecting:
                    current_page_items.append(item)

            if current_page_items:
                collected_data.append((page, current_page_items))
            elif not collecting and collected_data:
                break

        if not collected_data:
            return None

        filtered_pages = [
            Page(
                page=p.page,
                items=items,
                text="\n\n".join(i.value for i in items if i.value) or None,
                md="\n\n".join(i.md for i in items if i.md) or None,
            )
            for p, items in collected_data
        ]
        return self.build_result_from_pages(filtered_pages)

    @staticmethod
    async def from_llama_result(llama_result: JobResult) -> "ParseResult":
        """Convert LlamaParse result to our ParseResult model."""
        # Markdown endpoint not always available, so we catch the exception and set markdown to None
        try:
            markdown = await llama_result.aget_markdown()
        except Exception:
            markdown = None
        pages = list(llama_result.pages or [])
        # Some deployments occasionally report 0 in job metadata even when pages are present.
        page_count = int(
            getattr(llama_result.job_metadata, "job_pages", 0) or len(pages)
        )
        result = ParseResult(
            job_id=llama_result.job_id,
            markdown=markdown,
            text=await llama_result.aget_text(),
            pages=pages,
            page_count=page_count,
            raw_json=await llama_result.aget_json(),
        )
        return result

    @staticmethod
    def merge_results(
        results: list["ParseResult"], source_names: list[str] | None = None
    ) -> "ParseResult":
        """Merge multiple ParseResults into a single result with continuous page numbering.

        This is useful when multiple PDFs belong to the same invoice and need to be
        processed together as a single document.

        Args:
            results: List of ParseResult objects to merge
            source_names: Optional list of source filenames for reference

        Returns:
            A single ParseResult with all pages renumbered continuously
        """
        if not results:
            raise ValueError("Cannot merge empty list of results")

        if len(results) == 1:
            return results[0]

        merged_pages: list[Page] = []
        merged_markdowns: list[str] = []
        merged_texts: list[str] = []
        page_offset = 0

        for idx, result in enumerate(results):
            source_name = (
                source_names[idx] if source_names and idx < len(source_names) else None
            )

            # Add separator between documents in markdown
            if source_name and merged_markdowns:
                merged_markdowns.append(f"\n\n---\n\n## Document: {source_name}\n\n")
            elif source_name and not merged_markdowns:
                merged_markdowns.append(f"## Document: {source_name}\n\n")

            if result.markdown:
                merged_markdowns.append(result.markdown)
            if result.text:
                merged_texts.append(result.text)

            # Renumber pages with offset to ensure continuous numbering
            for page in result.pages:
                new_page = Page(
                    page=page.page + page_offset,
                    items=page.items,
                    text=page.text,
                    md=page.md,
                    images=getattr(page, "images", None),
                    layout=getattr(page, "layout", None),
                    structuredData=getattr(page, "structuredData", None),
                )
                merged_pages.append(new_page)

            page_offset += result.page_count

        # Combine job_ids for reference
        job_ids = [r.job_id for r in results]
        combined_job_id = "|".join(job_ids)

        return ParseResult(
            job_id=combined_job_id,
            markdown="\n\n".join(merged_markdowns) if merged_markdowns else None,
            text="\n\n".join(merged_texts),
            pages=merged_pages,
            page_count=len(merged_pages),
            raw_json=None,  # Raw JSON is not merged as it would be complex
        )


class ExtractedRules(BaseModel):
    """Extrae solo las restricciones clave en texto simple."""

    reglas_clave: list[str] = Field(
        ...,
        description="Lista de reglas importantes. Ej: 'Tope de pintura $4500', 'Daños ocultos permitidos solo con nota técnica'.",
    )
    deducible: float = Field(..., description="El porcentaje de deducible (0.05).")


class ItemCheck(BaseModel):
    """Validación de una sola línea."""

    item: str = Field(..., description="Nombre de la pieza o servicio")
    costo: float
    decision: str = Field(
        ..., description="Usa SOLO: 'APROBADO', 'RECHAZADO' o 'JUSTIFICADO_POR_NOTA'"
    )
    explicacion: str = Field(
        ..., description="Breve razón. Ej: 'Cumple cláusula de daños ocultos'."
    )


class ReporteValidation(BaseModel):
    """El resultado final para el Frontend."""

    items: list[ItemCheck]
    total_aprobado: float
