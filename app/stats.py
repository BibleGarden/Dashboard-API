from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from database import create_connection
from auth import RequireJWT
from config import PUBLIC_DB_NAME

router = APIRouter(prefix="/stats", tags=["Statistics"])

AI_ENDPOINT_PREFIX = "/api/ai/"
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


@router.get("/summary", operation_id="get_stats_summary")
def get_stats_summary(days: int = Query(30, ge=1, le=365), username: str = RequireJWT):
    connection = create_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        db = PUBLIC_DB_NAME

        # Totals for the period (exclude _total_ synthetic rows)
        cursor.execute(f"""
            SELECT
                COALESCE(SUM(request_count), 0)                   AS total_requests,
                COALESCE(SUM(error_count), 0)                     AS total_errors,
                COALESCE(ROUND(AVG(avg_response_time_ms)), 0)     AS avg_response_time_ms
            FROM {db}.api_request_daily_stats
            WHERE date >= CURDATE() - INTERVAL %s DAY
              AND endpoint != '_total_'
        """, (days,))
        totals = cursor.fetchone()

        # Totals for the previous period of the same length (for trend deltas)
        cursor.execute(f"""
            SELECT
                COALESCE(SUM(request_count), 0)                   AS total_requests,
                COALESCE(SUM(error_count), 0)                     AS total_errors,
                COALESCE(ROUND(AVG(avg_response_time_ms)), 0)     AS avg_response_time_ms
            FROM {db}.api_request_daily_stats
            WHERE date >= CURDATE() - INTERVAL %s DAY
              AND date <  CURDATE() - INTERVAL %s DAY
              AND endpoint != '_total_'
        """, (days * 2, days))
        previous_totals = cursor.fetchone()

        # Unique IPs from raw table (last RAW_RETENTION_DAYS days max)
        cursor.execute(f"""
            SELECT COUNT(DISTINCT client_ip) AS unique_ips
            FROM {db}.api_requests
            WHERE created_at >= NOW() - INTERVAL LEAST(%s, {RAW_RETENTION_DAYS}) DAY
        """, (days,))
        raw_ips = cursor.fetchone()

        # Unique IPs for the previous period; not available when the raw
        # table no longer covers it (rows are purged after RAW_RETENTION_DAYS)
        previous_unique_ips = None
        if days <= RAW_RETENTION_DAYS:
            cursor.execute(f"""
                SELECT COUNT(DISTINCT client_ip) AS unique_ips
                FROM {db}.api_requests
                WHERE created_at >= NOW() - INTERVAL %s DAY
                  AND created_at <  NOW() - INTERVAL %s DAY
            """, (days * 2, days))
            previous_unique_ips = cursor.fetchone()["unique_ips"] or 0

        # Traffic groups (scripture / ai / other): aggregated + today's live data
        cursor.execute(f"""
            SELECT grp,
                   SUM(requests) AS requests,
                   SUM(errors)   AS errors,
                   ROUND(AVG(avg_response_time_ms)) AS avg_response_time_ms
            FROM (
                SELECT {GROUP_CASE} AS grp,
                       request_count AS requests, error_count AS errors,
                       avg_response_time_ms
                FROM {db}.api_request_daily_stats
                WHERE date >= CURDATE() - INTERVAL %s DAY
                  AND endpoint != '_total_'
                UNION ALL
                SELECT {GROUP_CASE} AS grp,
                       COUNT(*) AS requests,
                       SUM(status_code >= 400) AS errors,
                       ROUND(AVG(response_time_ms)) AS avg_response_time_ms
                FROM {db}.api_requests
                WHERE DATE(created_at) = CURDATE()
                GROUP BY grp
            ) combined
            GROUP BY grp
        """, (days,))
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

        # Daily breakdown: use _total_ rows from aggregated stats + today's live data
        cursor.execute(f"""
            SELECT date, requests, unique_ips,
                   avg_response_time_ms, errors
            FROM (
                SELECT date, request_count AS requests, unique_ips,
                       avg_response_time_ms, error_count AS errors
                FROM {db}.api_request_daily_stats
                WHERE date >= CURDATE() - INTERVAL %s DAY
                  AND endpoint = '_total_'
                UNION ALL
                SELECT CURDATE() AS date, COUNT(*) AS requests,
                       COUNT(DISTINCT client_ip) AS unique_ips,
                       ROUND(AVG(response_time_ms)) AS avg_response_time_ms,
                       SUM(status_code >= 400) AS errors
                FROM {db}.api_requests
                WHERE DATE(created_at) = CURDATE()
                HAVING requests > 0
            ) combined
            ORDER BY date
        """, (days,))
        daily = cursor.fetchall()

        # Daily requests split by traffic group (for the chart)
        cursor.execute(f"""
            SELECT date, grp, SUM(requests) AS requests
            FROM (
                SELECT date, {GROUP_CASE} AS grp, request_count AS requests
                FROM {db}.api_request_daily_stats
                WHERE date >= CURDATE() - INTERVAL %s DAY
                  AND endpoint != '_total_'
                UNION ALL
                SELECT CURDATE() AS date, {GROUP_CASE} AS grp,
                       COUNT(*) AS requests
                FROM {db}.api_requests
                WHERE DATE(created_at) = CURDATE()
                GROUP BY grp
            ) combined
            GROUP BY date, grp
            ORDER BY date
        """, (days,))
        daily_groups = cursor.fetchall()

        # Top endpoints (aggregated + today's live data)
        cursor.execute(f"""
            SELECT endpoint, SUM(requests) AS requests, SUM(unique_ips) AS unique_ips,
                   ROUND(AVG(avg_response_time_ms)) AS avg_response_time_ms, SUM(errors) AS errors
            FROM (
                SELECT endpoint, request_count AS requests, unique_ips,
                       avg_response_time_ms, error_count AS errors
                FROM {db}.api_request_daily_stats
                WHERE date >= CURDATE() - INTERVAL %s DAY
                  AND endpoint != '_total_'
                UNION ALL
                SELECT endpoint, COUNT(*) AS requests,
                       COUNT(DISTINCT client_ip) AS unique_ips,
                       ROUND(AVG(response_time_ms)) AS avg_response_time_ms,
                       SUM(status_code >= 400) AS errors
                FROM {db}.api_requests
                WHERE DATE(created_at) = CURDATE()
                GROUP BY endpoint
            ) combined
            GROUP BY endpoint
            ORDER BY requests DESC
            LIMIT {TOP_ENDPOINTS_LIMIT}
        """, (days,))
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
            WHERE DATE(created_at) = CURDATE()
        """)
        today = cursor.fetchone()

        return {
            "period_days": days,
            "totals": {
                "total_requests": totals["total_requests"] + (today["requests"] or 0),
                "total_errors": totals["total_errors"] + (today["errors"] or 0),
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


@router.get("/recent", operation_id="get_recent_requests")
def get_recent_requests(
    limit: int = Query(50, ge=1, le=200),
    endpoint: Optional[str] = Query(None, max_length=255),
    status: Optional[str] = Query(None, pattern="^[1-5][0-9xX]{2}$"),
    method: Optional[str] = Query(None, max_length=10),
    client_ip: Optional[str] = Query(None, max_length=45),
    username: str = RequireJWT,
):
    connection = create_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        db = PUBLIC_DB_NAME

        where_clauses = []
        params = []
        if endpoint:
            where_clauses.append("endpoint LIKE %s")
            params.append(f"%{endpoint}%")
        if status:
            where_clauses.append("status_code LIKE %s")
            params.append(status.lower().replace("x", "_"))
        if method:
            where_clauses.append("method = %s")
            params.append(method.upper())
        if client_ip:
            where_clauses.append("client_ip LIKE %s")
            params.append(f"%{client_ip}%")
        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        cursor.execute(f"""
            SELECT id, endpoint, method, status_code, response_time_ms,
                   client_ip, user_agent, created_at
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
