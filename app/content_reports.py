from datetime import datetime
from typing import Literal, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, field_serializer

from auth import RequireJWT
from config import PUBLIC_DB_NAME
from database import create_connection
from utc_time import mysql_datetime_as_utc

router = APIRouter(prefix="/content-reports", tags=["Content reports"])
ContentReportStatus = Literal[
    "unreviewed",
    "not_significant",
    "needs_investigation",
    "action_taken",
]


class ContentReportItem(BaseModel):
    id: int
    content_type: Literal["question", "scripture"]
    content_text: str
    user_comment: Optional[str]
    language: Literal["ru", "en", "uk"]
    status: ContentReportStatus
    created_at: datetime = Field(description="UTC time with a Z suffix")

    @field_serializer("created_at")
    def serialize_created_at(self, value: datetime) -> str:
        return mysql_datetime_as_utc(value)


class ContentReportsResponse(BaseModel):
    items: list[ContentReportItem]
    count: int


class ContentReportStatusUpdate(BaseModel):
    status: ContentReportStatus


class ContentReportStatusResponse(BaseModel):
    id: int
    status: ContentReportStatus


@router.get(
    "",
    response_model=ContentReportsResponse,
    operation_id="get_content_reports",
)
def get_content_reports(
    limit: int = Query(50, ge=1, le=100),
    after_id: Optional[int] = Query(None, ge=0),
    before_id: Optional[int] = Query(None, ge=1),
    status: Optional[ContentReportStatus] = Query(None),
    username: str = RequireJWT,
):
    if after_id is not None and before_id is not None:
        raise HTTPException(
            status_code=422,
            detail="after_id and before_id are mutually exclusive",
        )

    connection = create_connection()
    if connection is None:
        raise HTTPException(
            status_code=500, detail="Content report storage is unavailable"
        )

    cursor = connection.cursor(dictionary=True)
    try:
        db = PUBLIC_DB_NAME
        conditions: list[str] = []
        params: list[object] = []
        order = "DESC"

        if status is not None:
            conditions.append("status = %s")
            params.append(status)

        if after_id is not None:
            conditions.append("id > %s")
            params.append(after_id)
            order = "ASC"
        elif before_id is not None:
            conditions.append("id < %s")
            params.append(before_id)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        cursor.execute(
            f"""
            SELECT id, content_type, content_text, user_comment, language,
                   status, created_at
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


@router.patch(
    "/{report_id}/status",
    response_model=ContentReportStatusResponse,
    operation_id="update_content_report_status",
)
def update_content_report_status(
    report_id: int,
    update: ContentReportStatusUpdate,
    username: str = RequireJWT,
):
    connection = create_connection()
    if connection is None:
        raise HTTPException(
            status_code=500, detail="Content report storage is unavailable"
        )

    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            f"""
            UPDATE {PUBLIC_DB_NAME}.ai_content_reports
            SET status = %s
            WHERE id = %s
            """,
            (update.status, report_id),
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Content report not found")

        connection.commit()
        return ContentReportStatusResponse(id=report_id, status=update.status)
    except HTTPException:
        connection.rollback()
        raise
    except Exception:
        connection.rollback()
        raise HTTPException(
            status_code=500,
            detail="Failed to update content report status",
        ) from None
    finally:
        cursor.close()
        connection.close()
