from datetime import datetime
from typing import Literal, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from auth import RequireJWT
from config import PUBLIC_DB_NAME
from database import create_connection


router = APIRouter(prefix="/content-reports", tags=["Content reports"])


class ContentReportItem(BaseModel):
    id: int
    content_type: Literal["question", "scripture"]
    content_text: str
    user_comment: Optional[str]
    language: Literal["ru", "en", "uk"]
    created_at: datetime = Field(
        description="Report creation time in the database's Europe/Moscow timezone"
    )


class ContentReportsResponse(BaseModel):
    items: list[ContentReportItem]
    count: int


@router.get(
    "",
    response_model=ContentReportsResponse,
    operation_id="get_content_reports",
)
def get_content_reports(
    limit: int = Query(50, ge=1, le=100),
    after_id: Optional[int] = Query(None, ge=0),
    before_id: Optional[int] = Query(None, ge=1),
    username: str = RequireJWT,
):
    if after_id is not None and before_id is not None:
        raise HTTPException(
            status_code=422,
            detail="after_id and before_id are mutually exclusive",
        )

    connection = create_connection()
    if connection is None:
        raise HTTPException(status_code=500, detail="Content report storage is unavailable")

    cursor = connection.cursor(dictionary=True)
    try:
        db = PUBLIC_DB_NAME
        where = ""
        params: tuple[int, ...] = ()
        order = "DESC"

        if after_id is not None:
            where = "WHERE id > %s"
            params = (after_id,)
            order = "ASC"
        elif before_id is not None:
            where = "WHERE id < %s"
            params = (before_id,)

        cursor.execute(
            f"""
            SELECT id, content_type, content_text, user_comment, language,
                   created_at
            FROM {db}.ai_content_reports
            {where}
            ORDER BY id {order}
            LIMIT %s
            """,
            (*params, limit),
        )
        items = cursor.fetchall()
        return ContentReportsResponse(items=items, count=len(items))
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Failed to load content reports",
        ) from None
    finally:
        cursor.close()
        connection.close()
