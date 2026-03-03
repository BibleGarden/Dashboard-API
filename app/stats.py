from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from database import create_connection
from auth import RequireJWT
from config import PUBLIC_DB_NAME

router = APIRouter(prefix="/stats", tags=["Statistics"])


@router.get("/summary", operation_id="get_stats_summary")
def get_stats_summary(days: int = Query(30, ge=1, le=365), username: str = RequireJWT):
    connection = create_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        db = PUBLIC_DB_NAME

        # Totals for the period
        cursor.execute(f"""
            SELECT
                COALESCE(SUM(request_count), 0)                   AS total_requests,
                COALESCE(SUM(error_count), 0)                     AS total_errors,
                COALESCE(ROUND(AVG(avg_response_time_ms)), 0)     AS avg_response_time_ms
            FROM {db}.api_request_daily_stats
            WHERE date >= CURDATE() - INTERVAL %s DAY
        """, (days,))
        totals = cursor.fetchone()

        # Unique IPs for the period (approximate — sum of daily uniques)
        cursor.execute(f"""
            SELECT COUNT(DISTINCT date, endpoint) AS data_points,
                   COALESCE(SUM(unique_ips), 0)   AS total_unique_ips_approx
            FROM {db}.api_request_daily_stats
            WHERE date >= CURDATE() - INTERVAL %s DAY
        """, (days,))
        ips_row = cursor.fetchone()

        # Try to get more accurate unique IPs from raw table (last 14 days max)
        cursor.execute(f"""
            SELECT COUNT(DISTINCT client_ip) AS unique_ips
            FROM {db}.api_requests
            WHERE created_at >= NOW() - INTERVAL LEAST(%s, 14) DAY
        """, (days,))
        raw_ips = cursor.fetchone()

        # Daily breakdown (aggregated + today's live data)
        cursor.execute(f"""
            SELECT date, SUM(requests) AS requests, SUM(unique_ips) AS unique_ips,
                   ROUND(AVG(avg_response_time_ms)) AS avg_response_time_ms, SUM(errors) AS errors
            FROM (
                SELECT date, request_count AS requests, unique_ips,
                       avg_response_time_ms, error_count AS errors
                FROM {db}.api_request_daily_stats
                WHERE date >= CURDATE() - INTERVAL %s DAY
                UNION ALL
                SELECT CURDATE() AS date, COUNT(*) AS requests,
                       COUNT(DISTINCT client_ip) AS unique_ips,
                       ROUND(AVG(response_time_ms)) AS avg_response_time_ms,
                       SUM(status_code >= 400) AS errors
                FROM {db}.api_requests
                WHERE DATE(created_at) = CURDATE()
                HAVING requests > 0
            ) combined
            GROUP BY date
            ORDER BY date
        """, (days,))
        daily = cursor.fetchall()

        # Top endpoints (aggregated + today's live data)
        cursor.execute(f"""
            SELECT endpoint, SUM(requests) AS requests, SUM(unique_ips) AS unique_ips,
                   ROUND(AVG(avg_response_time_ms)) AS avg_response_time_ms, SUM(errors) AS errors
            FROM (
                SELECT endpoint, request_count AS requests, unique_ips,
                       avg_response_time_ms, error_count AS errors
                FROM {db}.api_request_daily_stats
                WHERE date >= CURDATE() - INTERVAL %s DAY
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
            LIMIT 20
        """, (days,))
        top_endpoints = cursor.fetchall()

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
            "today": {
                "requests": today["requests"] or 0,
                "unique_ips": today["unique_ips"] or 0,
                "avg_response_time_ms": today["avg_response_time_ms"] or 0,
                "errors": today["errors"] or 0,
            },
            "daily": daily,
            "top_endpoints": top_endpoints,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        connection.close()


@router.get("/recent", operation_id="get_recent_requests")
def get_recent_requests(limit: int = Query(50, ge=1, le=200), username: str = RequireJWT):
    connection = create_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        db = PUBLIC_DB_NAME

        cursor.execute(f"""
            SELECT id, endpoint, method, status_code, response_time_ms,
                   client_ip, user_agent, created_at
            FROM {db}.api_requests
            ORDER BY id DESC
            LIMIT %s
        """, (limit,))
        rows = cursor.fetchall()

        return {"items": rows, "count": len(rows)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        connection.close()
