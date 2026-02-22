"""AI parsing endpoints."""

from fastapi import APIRouter, Depends

from app.ai.parser import AIParserService
from app.api.deps import get_ai_parser
from app.schemas.ai import AIParseRequest, AIParsedEntry

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/parse", response_model=AIParsedEntry)
async def parse_entry_text(
    payload: AIParseRequest,
    parser: AIParserService = Depends(get_ai_parser),
) -> AIParsedEntry:
    """Parse operator free text into a structured entry payload."""

    return await parser.parse(payload.text)
