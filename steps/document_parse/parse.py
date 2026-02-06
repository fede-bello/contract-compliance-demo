import httpx
from llama_cloud_services import LlamaParse

from models import File, ParseResult
from utils.logging import get_logger
from utils.settings import get_settings

logger = get_logger(__name__)

PARSE_SYSTEM_PROMPT = (
    """Check If there is  header row, if not, fill the Header with 'BLANK'"""
)


async def parse_document(files: list[File], **kwargs) -> ParseResult:
    """Parse documeent(s) to markdown with page-level content and detected tables.

    Supports both single file and multiple files for the same invoice.
    When multiple files are provided, results are merged into a single ParseResult
    with continuous page numbering.

    Args:
        files: List of File objects with path and name attributes
        **kwargs: Additional arguments for LlamaParse

    Returns:
        ParseResult with markdown, page-level content, and detected tables
    """
    file_paths = [f.path for f in files]
    filenames = [f.name for f in files]

    logger.info(
        "fetching_documents | file_count=%s | filenames=%s | kwargs=%s",
        len(file_paths),
        filenames,
        kwargs,
    )

    try:
        config = get_settings()
        # Default parameters
        http_client = httpx.AsyncClient(verify=False, timeout=60)
        params = {
            "api_key": config.LLAMA_CLOUD_API_KEY,
            "base_url": config.LLAMA_CLOUD_BASE_URL,
            "custom_client": http_client,
            "num_workers": min(4, len(file_paths)),  # Parallelize when multiple files
        }
        # Update with kwargs
        params.update(kwargs)

        parser = LlamaParse(**params)

        try:
            # Parse all files and merge results
            llama_results = await parser.aparse(
                file_paths, extra_info={"filenames": filenames}
            )
            # llama_results is a list of JobResult when multiple files are passed
            parse_results = [
                await ParseResult.from_llama_result(result) for result in llama_results
            ]
            parse_result = ParseResult.merge_results(parse_results, filenames)
        finally:
            await http_client.aclose()

        logger.info(
            "documents_parsed | filenames=%s | pages=%s | tables_found=%s",
            filenames,
            parse_result.page_count,
            parse_result.table_count,
        )

        return parse_result
    except Exception as e:
        logger.error(
            "parse_failed | error=%s | error_type=%s", str(e), type(e).__name__
        )
        raise
