from typing import Annotated, Literal, Optional

from fastapi import APIRouter, HTTPException, Query
from database import create_connection
from auth import RequireJWT
from config import PUBLIC_DB_NAME
from models import RecentRequestsResponseModel, StatsSummaryResponseModel

router = APIRouter(prefix="/stats", tags=["Statistics"])

RAW_RETENTION_DAYS = 14
SLOW_ENDPOINTS_MIN_REQUESTS = 10
SLOW_ENDPOINTS_LIMIT = 10
TOP_ENDPOINTS_LIMIT = 20

# Classifies a normalized endpoint into a traffic group:
# ai — AI endpoints, scripture — public scripture API, other — everything else.
GROUP_CASE = """
    CASE
        WHEN endpoint LIKE '/api/ai/%' THEN 'ai'
        WHEN endpoint LIKE '/api/%' THEN 'scripture'
        ELSE 'other'
    END
"""
APPLICATIONS = ("bible-garden", "lampada", "ops", "unknown")

# New aggregate days have one overall row per endpoint. Historical rows from
# before the key split have only application='unknown'.
OVERALL_DAILY_FILTER = """
    (daily_stats.application = 'all' OR (
        daily_stats.application = 'unknown' AND NOT EXISTS (
            SELECT 1 FROM {db}.api_request_daily_stats overall
            WHERE overall.date = daily_stats.date
              AND overall.endpoint = daily_stats.endpoint
              AND overall.application = 'all'
        )
    ))
"""


def escape_like_literal(value: str) -> str:
    """Escape a user substring for LIKE ... ESCAPE '='."""
    return value.replace("=", "==").replace("%", "=%").replace("_", "=_")


@router.get(
    "/summary",
    operation_id="get_stats_summary",
    response_model=StatsSummaryResponseModel,
)
def get_stats_summary(
    days: int = Query(30, ge=1, le=365),
    top_group: Annotated[
        Optional[Literal["scripture", "ai", "other"]], Query()
    ] = None,
    top_endpoint: Annotated[Optional[str], Query(max_length=255)] = None,
    username: str = RequireJWT,
):
    connection = create_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        db = PUBLIC_DB_NAME

        current_start_days_ago = days - 1
        previous_start_days_ago = days * 2 - 1

        # Current period: historical daily aggregates through yesterday plus
        # today's raw requests. Synthetic _total_ rows are excluded.
        cursor.execute(f"""
            SELECT
                COALESCE(SUM(requests), 0) AS total_requests,
                COALESCE(SUM(errors), 0) AS total_errors,
                COALESCE(ROUND(
                    SUM(response_time_sum) / NULLIF(SUM(requests), 0)
                ), 0) AS avg_response_time_ms
            FROM (
                SELECT request_count AS requests,
                       error_count AS errors,
                       avg_response_time_ms * request_count AS response_time_sum
                FROM {db}.api_request_daily_stats daily_stats
                WHERE date >= CURDATE() - INTERVAL %s DAY
                  AND date < CURDATE()
                  AND endpoint != '_total_'
                  AND {OVERALL_DAILY_FILTER.format(db=db)}
                UNION ALL
                SELECT COUNT(*) AS requests,
                       COALESCE(SUM(status_code >= 400), 0) AS errors,
                       COALESCE(SUM(response_time_ms), 0) AS response_time_sum
                FROM {db}.api_requests
                WHERE created_at >= CURDATE()
                  AND created_at < CURDATE() + INTERVAL 1 DAY
            ) combined
        """, (current_start_days_ago,))
        totals = cursor.fetchone()

        # Totals for the previous period of the same length (for trend deltas)
        cursor.execute(f"""
            SELECT
                COALESCE(SUM(request_count), 0) AS total_requests,
                COALESCE(SUM(error_count), 0) AS total_errors,
                COALESCE(ROUND(
                    SUM(avg_response_time_ms * request_count)
                    / NULLIF(SUM(request_count), 0)
                ), 0) AS avg_response_time_ms
            FROM {db}.api_request_daily_stats daily_stats
            WHERE date >= CURDATE() - INTERVAL %s DAY
              AND date <  CURDATE() - INTERVAL %s DAY
              AND endpoint != '_total_'
              AND {OVERALL_DAILY_FILTER.format(db=db)}
        """, (previous_start_days_ago, current_start_days_ago))
        previous_totals = cursor.fetchone()

        # Unique IP-based pseudonyms from the available raw portion.
        current_raw_start_days_ago = min(days, RAW_RETENTION_DAYS) - 1
        cursor.execute(f"""
            SELECT COUNT(DISTINCT client_ip) AS unique_ips
            FROM {db}.api_requests
            WHERE created_at >= CURDATE() - INTERVAL %s DAY
              AND created_at < CURDATE() + INTERVAL 1 DAY
        """, (current_raw_start_days_ago,))
        raw_ips = cursor.fetchone()

        # Unique IP-based pseudonyms for the previous period; unavailable when raw
        # retention window cannot contain that whole calendar interval.
        previous_unique_ips = None
        if days * 2 <= RAW_RETENTION_DAYS:
            cursor.execute(f"""
                SELECT COUNT(DISTINCT client_ip) AS unique_ips
                FROM {db}.api_requests
                WHERE created_at >= CURDATE() - INTERVAL %s DAY
                  AND created_at < CURDATE() - INTERVAL %s DAY
            """, (previous_start_days_ago, current_start_days_ago))
            previous_unique_ips = cursor.fetchone()["unique_ips"] or 0

        # Traffic groups (scripture / ai / other): aggregated + today's live data
        cursor.execute(f"""
            SELECT grp,
                   SUM(requests) AS requests,
                   SUM(errors)   AS errors,
                   ROUND(
                       SUM(response_time_sum) / NULLIF(SUM(requests), 0)
                   ) AS avg_response_time_ms
            FROM (
                SELECT {GROUP_CASE} AS grp,
                       request_count AS requests, error_count AS errors,
                       avg_response_time_ms * request_count AS response_time_sum
                FROM {db}.api_request_daily_stats daily_stats
                WHERE date >= CURDATE() - INTERVAL %s DAY
                  AND date < CURDATE()
                  AND endpoint != '_total_'
                  AND {OVERALL_DAILY_FILTER.format(db=db)}
                UNION ALL
                SELECT {GROUP_CASE} AS grp,
                       COUNT(*) AS requests,
                       SUM(status_code >= 400) AS errors,
                       SUM(response_time_ms) AS response_time_sum
                FROM {db}.api_requests
                WHERE created_at >= CURDATE()
                  AND created_at < CURDATE() + INTERVAL 1 DAY
                GROUP BY grp
            ) combined
            GROUP BY grp
        """, (current_start_days_ago,))
        groups = {
            "scripture": {"requests": 0, "errors": 0, "avg_response_time_ms": 0},
            "ai":        {"requests": 0, "errors": 0, "avg_response_time_ms": 0},
            "other":     {"requests": 0, "errors": 0, "avg_response_time_ms": 0},
        }
        for row in cursor.fetchall():
            groups[row["grp"]] = {
                "requests": row["requests"] or 0,
                "errors": row["errors"] or 0,
                "avg_response_time_ms": row["avg_response_time_ms"] or 0,
            }

        # Historical unknown rows remain visible; today's raw rows are live.
        cursor.execute(f"""
            SELECT application, SUM(requests) AS requests,
                   SUM(errors) AS errors,
                   ROUND(SUM(response_time_sum) / NULLIF(SUM(requests), 0))
                       AS avg_response_time_ms
            FROM (
                SELECT application, request_count AS requests,
                       error_count AS errors,
                       avg_response_time_ms * request_count AS response_time_sum
                FROM {db}.api_request_daily_stats
                WHERE date >= CURDATE() - INTERVAL %s DAY
                  AND date < CURDATE() AND endpoint != '_total_'
                  AND application != 'all'
                UNION ALL
                SELECT application, COUNT(*), SUM(status_code >= 400),
                       SUM(response_time_ms)
                FROM {db}.api_requests
                WHERE created_at >= CURDATE()
                  AND created_at < CURDATE() + INTERVAL 1 DAY
                GROUP BY application
            ) combined
            GROUP BY application
        """, (current_start_days_ago,))
        application_rows = {row["application"]: row for row in cursor.fetchall()}
        unexpected_applications = application_rows.keys() - set(APPLICATIONS)
        if unexpected_applications:
            raise ValueError(f"Unknown request applications: {sorted(unexpected_applications)}")
        applications = [
            {
                "application": application,
                "requests": application_rows.get(application, {}).get("requests") or 0,
                "errors": application_rows.get(application, {}).get("errors") or 0,
                "avg_response_time_ms": application_rows.get(application, {}).get(
                    "avg_response_time_ms"
                ) or 0,
            }
            for application in APPLICATIONS
        ]

        # Daily breakdown: use _total_ rows from aggregated stats + today's live data
        cursor.execute(f"""
            SELECT date, requests, unique_ips,
                   avg_response_time_ms, errors
            FROM (
                SELECT date, request_count AS requests, unique_ips,
                       avg_response_time_ms, error_count AS errors
                FROM {db}.api_request_daily_stats daily_stats
                WHERE date >= CURDATE() - INTERVAL %s DAY
                  AND date < CURDATE()
                  AND endpoint = '_total_'
                  AND (application = 'all' OR (
                      application = 'unknown' AND NOT EXISTS (
                          SELECT 1 FROM {db}.api_request_daily_stats all_totals
                          WHERE all_totals.date = daily_stats.date
                            AND all_totals.endpoint = '_total_'
                            AND all_totals.application = 'all'
                      )
                  ))
                UNION ALL
                SELECT CURDATE() AS date, COUNT(*) AS requests,
                       COUNT(DISTINCT client_ip) AS unique_ips,
                       ROUND(AVG(response_time_ms)) AS avg_response_time_ms,
                       SUM(status_code >= 400) AS errors
                FROM {db}.api_requests
                WHERE created_at >= CURDATE()
                  AND created_at < CURDATE() + INTERVAL 1 DAY
                HAVING requests > 0
            ) combined
            ORDER BY date
        """, (current_start_days_ago,))
        daily = cursor.fetchall()

        # Daily requests split by traffic group (for the chart)
        cursor.execute(f"""
            SELECT date, grp, SUM(requests) AS requests
            FROM (
                SELECT date, {GROUP_CASE} AS grp, request_count AS requests
                FROM {db}.api_request_daily_stats daily_stats
                WHERE date >= CURDATE() - INTERVAL %s DAY
                  AND date < CURDATE()
                  AND endpoint != '_total_'
                  AND {OVERALL_DAILY_FILTER.format(db=db)}
                UNION ALL
                SELECT CURDATE() AS date, {GROUP_CASE} AS grp,
                       COUNT(*) AS requests
                FROM {db}.api_requests
                WHERE created_at >= CURDATE()
                  AND created_at < CURDATE() + INTERVAL 1 DAY
                GROUP BY grp
            ) combined
            GROUP BY date, grp
            ORDER BY date
        """, (current_start_days_ago,))
        daily_groups = cursor.fetchall()

        # Top endpoints (aggregated + today's live data)
        top_where_clauses = []
        top_params = [current_start_days_ago]
        if top_group is not None:
            top_where_clauses.append("grp = %s")
            top_params.append(top_group)
        if top_endpoint is not None:
            top_where_clauses.append("endpoint LIKE %s ESCAPE '='")
            top_params.append(f"%{escape_like_literal(top_endpoint)}%")
        top_where_sql = (
            f"WHERE {' AND '.join(top_where_clauses)}" if top_where_clauses else ""
        )

        cursor.execute(f"""
            SELECT endpoint, SUM(requests) AS requests, SUM(unique_ips) AS unique_ips,
                   ROUND(
                       SUM(response_time_sum) / NULLIF(SUM(requests), 0)
                   ) AS avg_response_time_ms,
                   SUM(errors) AS errors
            FROM (
                SELECT endpoint, {GROUP_CASE} AS grp,
                       request_count AS requests, unique_ips,
                       avg_response_time_ms * request_count AS response_time_sum,
                       error_count AS errors
                FROM {db}.api_request_daily_stats daily_stats
                WHERE date >= CURDATE() - INTERVAL %s DAY
                  AND date < CURDATE()
                  AND endpoint != '_total_'
                  AND {OVERALL_DAILY_FILTER.format(db=db)}
                UNION ALL
                SELECT endpoint, {GROUP_CASE} AS grp,
                       COUNT(*) AS requests,
                       COUNT(DISTINCT client_ip) AS unique_ips,
                       SUM(response_time_ms) AS response_time_sum,
                       SUM(status_code >= 400) AS errors
                FROM {db}.api_requests
                WHERE created_at >= CURDATE()
                  AND created_at < CURDATE() + INTERVAL 1 DAY
                GROUP BY endpoint, grp
            ) combined
            {top_where_sql}
            GROUP BY endpoint
            ORDER BY requests DESC
            LIMIT {TOP_ENDPOINTS_LIMIT}
        """, tuple(top_params))
        top_endpoints = cursor.fetchall()

        # Slowest endpoints by avg response time over the raw retention window
        cursor.execute(f"""
            SELECT endpoint,
                   COUNT(*) AS requests,
                   ROUND(AVG(response_time_ms)) AS avg_response_time_ms,
                   MAX(response_time_ms) AS max_response_time_ms
            FROM {db}.api_requests
            WHERE created_at >= NOW() - INTERVAL {RAW_RETENTION_DAYS} DAY
            GROUP BY endpoint
            HAVING COUNT(*) >= %s
            ORDER BY avg_response_time_ms DESC
            LIMIT %s
        """, (SLOW_ENDPOINTS_MIN_REQUESTS, SLOW_ENDPOINTS_LIMIT))
        slow_endpoints = cursor.fetchall()

        # Also include today's live data from raw table
        cursor.execute(f"""
            SELECT
                COUNT(*)                          AS requests,
                COUNT(DISTINCT client_ip)          AS unique_ips,
                ROUND(AVG(response_time_ms))       AS avg_response_time_ms,
                SUM(status_code >= 400)            AS errors
            FROM {db}.api_requests
            WHERE created_at >= CURDATE()
              AND created_at < CURDATE() + INTERVAL 1 DAY
        """)
        today = cursor.fetchone()

        return {
            "period_days": days,
            "totals": {
                "total_requests": totals["total_requests"],
                "total_errors": totals["total_errors"],
                "avg_response_time_ms": totals["avg_response_time_ms"],
                "unique_ips": raw_ips["unique_ips"] or 0,
            },
            "previous_totals": {
                "total_requests": previous_totals["total_requests"],
                "total_errors": previous_totals["total_errors"],
                "avg_response_time_ms": previous_totals["avg_response_time_ms"],
                "unique_ips": previous_unique_ips,
            },
            "today": {
                "requests": today["requests"] or 0,
                "unique_ips": today["unique_ips"] or 0,
                "avg_response_time_ms": today["avg_response_time_ms"] or 0,
                "errors": today["errors"] or 0,
            },
            "groups": groups,
            "applications": applications,
            "daily": daily,
            "daily_groups": daily_groups,
            "top_endpoints": top_endpoints,
            "slow_endpoints": slow_endpoints,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        connection.close()


@router.get(
    "/recent",
    operation_id="get_recent_requests",
    response_model=RecentRequestsResponseModel,
)
def get_recent_requests(
    limit: int = Query(50, ge=1, le=200),
    endpoint: Annotated[Optional[str], Query(max_length=255)] = None,
    status: Annotated[
        Optional[str], Query(pattern="^(?:[1-5][0-9]{2}|[1-5][xX]{2})$")
    ] = None,
    method: Annotated[Optional[str], Query(max_length=10)] = None,
    client_pseudonym: Annotated[
        Optional[str], Query(min_length=1, max_length=40, pattern="^[0-9a-fA-F]+$")
    ] = None,
    application: Annotated[
        Optional[Literal["bible-garden", "lampada", "ops", "unknown"]], Query()
    ] = None,
    username: str = RequireJWT,
):
    connection = create_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        db = PUBLIC_DB_NAME

        where_clauses = []
        params = []
        if endpoint:
            where_clauses.append("endpoint LIKE %s ESCAPE '='")
            params.append(f"%{escape_like_literal(endpoint)}%")
        if status:
            where_clauses.append("status_code LIKE %s")
            params.append(status.lower().replace("x", "_"))
        if method:
            where_clauses.append("method = %s")
            params.append(method.upper())
        if client_pseudonym:
            where_clauses.append("client_ip LIKE %s ESCAPE '='")
            params.append(f"{escape_like_literal(client_pseudonym.lower())}%")
        if application:
            where_clauses.append("application = %s")
            params.append(application)
        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        cursor.execute(f"""
            SELECT id, endpoint, application, method, status_code, response_time_ms,
                   client_ip AS client_pseudonym, user_agent, created_at
            FROM {db}.api_requests
            {where_sql}
            ORDER BY id DESC
            LIMIT %s
        """, (*params, limit))
        rows = cursor.fetchall()

        return {"items": rows, "count": len(rows)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        connection.close()
