from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Annotated, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from database import create_connection
from auth import RequireJWT
from config import PUBLIC_DB_NAME
from models import (
    RecentRequestsResponseModel,
    StatsErrorsResponseModel,
    StatsSummaryResponseModel,
)
from utc_time import mysql_datetime_as_utc

router = APIRouter(prefix="/stats", tags=["Statistics"])

# Raw api_requests rows are purged after 14 days; hour windows must fit inside.
MAX_HOURS = 14 * 24
DEFAULT_HOURS = 24
MAX_RANGE_DAYS = 366
FAILURES_LIMIT = 100

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


@dataclass(frozen=True)
class PeriodParams:
    hours: Optional[int]
    date_from: Optional[date]
    date_to: Optional[date]


def period_params(
    hours: Annotated[Optional[int], Query(ge=1, le=MAX_HOURS)] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> PeriodParams:
    """Either a rolling window of hours or an inclusive range of database dates."""
    if hours is not None and (date_from is not None or date_to is not None):
        raise HTTPException(422, "Use either hours or date_from and date_to, not both")
    if (date_from is None) != (date_to is None):
        raise HTTPException(422, "date_from and date_to must be given together")
    if date_from is not None:
        if date_from > date_to:
            raise HTTPException(422, "date_from must not be after date_to")
        if (date_to - date_from).days + 1 > MAX_RANGE_DAYS:
            raise HTTPException(422, f"The date range must not exceed {MAX_RANGE_DAYS} days")
    return PeriodParams(hours, date_from, date_to)


@dataclass(frozen=True)
class StatsPeriod:
    """Current window [start, end) and previous window [previous_start, start),
    as naive database wall-clock datetimes."""
    hours: Optional[int]
    date_from: Optional[date]
    date_to: Optional[date]
    start: datetime
    end: datetime
    previous_start: datetime
    today: date

    @property
    def is_hours(self) -> bool:
        return self.hours is not None

    def as_response(self) -> dict:
        return {
            "mode": "hours" if self.is_hours else "dates",
            "hours": self.hours,
            "date_from": self.date_from,
            "date_to": self.date_to,
            "bucket": "hour" if self.is_hours else "day",
        }


def resolve_period(cursor, params: PeriodParams) -> StatsPeriod:
    cursor.execute("SELECT NOW() AS now, CURDATE() AS today")
    clock = cursor.fetchone()
    now, today = clock["now"], clock["today"]
    if params.date_from is None:
        hours = DEFAULT_HOURS if params.hours is None else params.hours
        start = now - timedelta(hours=hours)
        # DATETIME has second precision: [start, now + 1s) includes rows written at now.
        return StatsPeriod(hours, None, None, start, now + timedelta(seconds=1),
                           start - timedelta(hours=hours), today)
    if params.date_to > today:
        raise HTTPException(
            422, f"date_to {params.date_to} is after the database's today {today}"
        )
    days = (params.date_to - params.date_from).days + 1
    start = datetime.combine(params.date_from, time.min)
    return StatsPeriod(None, params.date_from, params.date_to, start,
                       datetime.combine(params.date_to + timedelta(days=1), time.min),
                       start - timedelta(days=days), today)


def fetch_raw_available_from(cursor, db) -> Optional[datetime]:
    cursor.execute(f"SELECT MIN(created_at) AS raw_from FROM {db}.api_requests")
    return cursor.fetchone()["raw_from"]


def raw_covers(raw_from: Optional[datetime], moment: datetime) -> bool:
    return raw_from is not None and moment >= raw_from


def fetch_counter_coverage(cursor, db, today: date) -> dict:
    """First date counted by each nullable daily counter.

    Days aggregated before the counters existed keep NULL. Today is always
    counted, because it is read from raw rows.
    """
    cursor.execute(f"""
        SELECT MIN(CASE WHEN server_error_count IS NOT NULL THEN date END)
                   AS server_errors_since,
               MIN(CASE WHEN degraded_count IS NOT NULL THEN date END)
                   AS degraded_since
        FROM {db}.api_request_daily_stats
        WHERE endpoint = '_total_' AND application = 'all'
    """)
    row = cursor.fetchone()
    return {
        key: row[key] if row[key] is not None else today
        for key in ("server_errors_since", "degraded_since")
    }


def fetch_raw_totals(cursor, db, start: datetime, end: datetime) -> dict:
    cursor.execute(f"""
        SELECT COUNT(*) AS requests,
               COUNT(DISTINCT client_ip) AS unique_clients,
               COALESCE(SUM(status_code >= 500), 0) AS server_errors,
               COALESCE(SUM(status_code BETWEEN 400 AND 499), 0) AS client_errors,
               COALESCE(SUM(degraded_reason IS NOT NULL), 0) AS degraded,
               COALESCE(ROUND(AVG(response_time_ms)), 0) AS avg_response_time_ms
        FROM {db}.api_requests
        WHERE created_at >= %s AND created_at < %s
    """, (start, end))
    return {key: int(value) for key, value in cursor.fetchone().items()}


def fetch_unique_clients(cursor, db, start: datetime, end: datetime) -> int:
    cursor.execute(f"""
        SELECT COUNT(DISTINCT client_ip) AS unique_clients
        FROM {db}.api_requests
        WHERE created_at >= %s AND created_at < %s
    """, (start, end))
    return cursor.fetchone()["unique_clients"]


def fetch_date_range_totals(cursor, db, first_day: date, last_day: date,
                            today: date) -> dict:
    """Totals over [first_day, last_day]: daily aggregates for days before
    today, raw rows for today. NULL daily counters are skipped by SUM."""
    raw_start = datetime.combine(max(first_day, today), time.min)
    raw_end = datetime.combine(last_day + timedelta(days=1), time.min)
    cursor.execute(f"""
        SELECT COALESCE(SUM(requests), 0) AS requests,
               COALESCE(SUM(server_errors), 0) AS server_errors,
               COALESCE(SUM(client_errors), 0) AS client_errors,
               COALESCE(SUM(degraded), 0) AS degraded,
               COALESCE(ROUND(
                   SUM(response_time_sum) / NULLIF(SUM(requests), 0)
               ), 0) AS avg_response_time_ms
        FROM (
            SELECT request_count AS requests,
                   server_error_count AS server_errors,
                   error_count - server_error_count AS client_errors,
                   degraded_count AS degraded,
                   avg_response_time_ms * request_count AS response_time_sum
            FROM {db}.api_request_daily_stats daily_stats
            WHERE date >= %s AND date <= %s AND date < %s
              AND endpoint != '_total_'
              AND {OVERALL_DAILY_FILTER.format(db=db)}
            UNION ALL
            SELECT COUNT(*),
                   COALESCE(SUM(status_code >= 500), 0),
                   COALESCE(SUM(status_code BETWEEN 400 AND 499), 0),
                   COALESCE(SUM(degraded_reason IS NOT NULL), 0),
                   COALESCE(SUM(response_time_ms), 0)
            FROM {db}.api_requests
            WHERE created_at >= %s AND created_at < %s
        ) combined
    """, (first_day, last_day, today, raw_start, raw_end))
    return {key: int(value) for key, value in cursor.fetchone().items()}


def fetch_applications(cursor, db, period: StatsPeriod) -> dict:
    """Per-application sums keyed by application; the period's raw part only
    in hours mode, daily aggregates plus today's raw rows in date mode."""
    raw_start = period.start if period.is_hours else max(
        period.start, datetime.combine(period.today, time.min)
    )
    daily_sql = ""
    params: tuple = ()
    if not period.is_hours:
        daily_sql = f"""
            SELECT application, request_count AS requests,
                   server_error_count AS server_errors,
                   degraded_count AS degraded,
                   avg_response_time_ms * request_count AS response_time_sum
            FROM {db}.api_request_daily_stats
            WHERE date >= %s AND date <= %s AND date < %s
              AND endpoint != '_total_' AND application != 'all'
            UNION ALL
        """
        params = (period.date_from, period.date_to, period.today)
    cursor.execute(f"""
        SELECT application,
               SUM(requests) AS requests,
               COALESCE(SUM(server_errors), 0) AS server_errors,
               COALESCE(SUM(degraded), 0) AS degraded,
               COALESCE(ROUND(SUM(response_time_sum) / NULLIF(SUM(requests), 0)), 0)
                   AS avg_response_time_ms
        FROM (
            {daily_sql}
            SELECT application, COUNT(*) AS requests,
                   SUM(status_code >= 500) AS server_errors,
                   SUM(degraded_reason IS NOT NULL) AS degraded,
                   SUM(response_time_ms) AS response_time_sum
            FROM {db}.api_requests
            WHERE created_at >= %s AND created_at < %s
            GROUP BY application
        ) combined
        GROUP BY application
    """, (*params, raw_start, period.end))
    rows = {row["application"]: row for row in cursor.fetchall()}
    unexpected_applications = rows.keys() - set(APPLICATIONS)
    if unexpected_applications:
        raise ValueError(f"Unknown request applications: {sorted(unexpected_applications)}")
    return rows


def fetch_hourly_series(cursor, db, period: StatsPeriod) -> list[dict]:
    cursor.execute(f"""
        SELECT TIMESTAMP(DATE(created_at), MAKETIME(HOUR(created_at), 0, 0)) AS bucket,
               COUNT(*) AS requests,
               COUNT(DISTINCT client_ip) AS unique_clients,
               SUM(status_code >= 500) AS server_errors,
               SUM(degraded_reason IS NOT NULL) AS degraded,
               ROUND(AVG(response_time_ms)) AS avg_response_time_ms,
               SUM({GROUP_CASE} = 'scripture') AS scripture_requests,
               SUM({GROUP_CASE} = 'ai') AS ai_requests
        FROM {db}.api_requests
        WHERE created_at >= %s AND created_at < %s
        GROUP BY bucket
    """, (period.start, period.end))
    rows = {row["bucket"]: row for row in cursor.fetchall()}
    series = []
    bucket = period.start.replace(minute=0, second=0, microsecond=0)
    while bucket < period.end:
        row = rows.pop(bucket, None)
        series.append({
            "bucket_start": mysql_datetime_as_utc(bucket),
            **{key: int(row[key]) if row else 0 for key in (
                "requests", "unique_clients", "server_errors", "degraded",
                "avg_response_time_ms", "scripture_requests", "ai_requests",
            )},
        })
        bucket += timedelta(hours=1)
    if rows:
        raise ValueError(f"Hourly buckets outside the window: {sorted(rows)}")
    return series


def fetch_daily_series(cursor, db, period: StatsPeriod, coverage: dict) -> list[dict]:
    raw_start = datetime.combine(period.today, time.min)
    cursor.execute(f"""
        SELECT date, request_count AS requests, unique_ips AS unique_clients,
               server_error_count AS server_errors, degraded_count AS degraded,
               avg_response_time_ms
        FROM {db}.api_request_daily_stats daily_stats
        WHERE date >= %s AND date <= %s AND date < %s
          AND endpoint = '_total_'
          AND {OVERALL_DAILY_FILTER.format(db=db)}
        UNION ALL
        SELECT DATE(created_at), COUNT(*), COUNT(DISTINCT client_ip),
               SUM(status_code >= 500), SUM(degraded_reason IS NOT NULL),
               ROUND(AVG(response_time_ms))
        FROM {db}.api_requests
        WHERE created_at >= %s AND created_at < %s
        GROUP BY DATE(created_at)
    """, (period.date_from, period.date_to, period.today, raw_start, period.end))
    totals = {row["date"]: row for row in cursor.fetchall()}

    cursor.execute(f"""
        SELECT date,
               SUM(CASE WHEN grp = 'scripture' THEN requests ELSE 0 END)
                   AS scripture_requests,
               SUM(CASE WHEN grp = 'ai' THEN requests ELSE 0 END) AS ai_requests
        FROM (
            SELECT date, {GROUP_CASE} AS grp, request_count AS requests
            FROM {db}.api_request_daily_stats daily_stats
            WHERE date >= %s AND date <= %s AND date < %s
              AND endpoint != '_total_'
              AND {OVERALL_DAILY_FILTER.format(db=db)}
            UNION ALL
            SELECT DATE(created_at), {GROUP_CASE}, COUNT(*)
            FROM {db}.api_requests
            WHERE created_at >= %s AND created_at < %s
            GROUP BY DATE(created_at), 2
        ) combined
        GROUP BY date
    """, (period.date_from, period.date_to, period.today, raw_start, period.end))
    groups = {row["date"]: row for row in cursor.fetchall()}

    series = []
    day = period.date_from
    while day <= period.date_to:
        row = totals.get(day)
        group_row = groups.get(day)
        entry = {
            "bucket_start": day.isoformat(),
            "requests": int(row["requests"]) if row else 0,
            "unique_clients": int(row["unique_clients"]) if row else 0,
            "avg_response_time_ms": int(row["avg_response_time_ms"]) if row else 0,
            "scripture_requests": int(group_row["scripture_requests"]) if group_row else 0,
            "ai_requests": int(group_row["ai_requests"]) if group_row else 0,
        }
        for counter, since_key in (("server_errors", "server_errors_since"),
                                   ("degraded", "degraded_since")):
            if day < coverage[since_key]:
                entry[counter] = None
            elif row is None:
                entry[counter] = 0
            elif row[counter] is None:
                raise ValueError(f"Daily {counter} is NULL on counted day {day}")
            else:
                entry[counter] = int(row[counter])
        series.append(entry)
        day += timedelta(days=1)
    return series


@router.get(
    "/summary",
    operation_id="get_stats_summary",
    response_model=StatsSummaryResponseModel,
)
def get_stats_summary(
    params: PeriodParams = Depends(period_params),
    username: str = RequireJWT,
):
    connection = create_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        db = PUBLIC_DB_NAME
        period = resolve_period(cursor, params)
        raw_from = fetch_raw_available_from(cursor, db)
        counters = ("server_errors", "client_errors", "degraded")

        if period.is_hours:
            # Everything comes from raw rows, which carry every counter.
            totals = fetch_raw_totals(cursor, db, period.start, period.end)
            if raw_covers(raw_from, period.previous_start):
                previous = fetch_raw_totals(cursor, db, period.previous_start, period.start)
            else:
                previous = dict.fromkeys(totals)
            coverage = {"server_errors_since": None, "degraded_since": None}
            counter_known = dict.fromkeys(counters, True)
            series = fetch_hourly_series(cursor, db, period)
        else:
            counter_since = fetch_counter_coverage(cursor, db, period.today)
            since = {
                "server_errors": counter_since["server_errors_since"],
                "client_errors": counter_since["server_errors_since"],
                "degraded": counter_since["degraded_since"],
            }
            previous_from = period.previous_start.date()
            previous_to = period.date_from - timedelta(days=1)

            totals = fetch_date_range_totals(
                cursor, db, period.date_from, period.date_to, period.today
            )
            # Unique clients exist only in raw rows: unknown for a range that
            # ends before them, partial (coverage.raw_since) for one that
            # starts before them.
            totals["unique_clients"] = (
                fetch_unique_clients(cursor, db, period.start, period.end)
                if raw_from is not None and period.end > raw_from else None
            )
            previous = fetch_date_range_totals(
                cursor, db, previous_from, previous_to, period.today
            )
            previous["unique_clients"] = (
                fetch_unique_clients(cursor, db, period.previous_start, period.start)
                if raw_covers(raw_from, period.previous_start) else None
            )
            counter_known = {}
            for counter in counters:
                counter_known[counter] = since[counter] <= period.date_to
                if not counter_known[counter]:
                    totals[counter] = None
                if since[counter] > previous_from:
                    previous[counter] = None
            coverage = {
                key: value if value > period.date_from else None
                for key, value in counter_since.items()
            }
            series = fetch_daily_series(cursor, db, period, counter_since)

        coverage["raw_since"] = (
            raw_from if raw_from is not None and period.start < raw_from else None
        )

        application_rows = fetch_applications(cursor, db, period)
        applications = []
        for application in APPLICATIONS:
            row = application_rows.get(application)
            entry = {
                "application": application,
                "requests": int(row["requests"]) if row else 0,
                "avg_response_time_ms": int(row["avg_response_time_ms"]) if row else 0,
            }
            for counter in ("server_errors", "degraded"):
                entry[counter] = (
                    (int(row[counter]) if row else 0)
                    if counter_known[counter] else None
                )
            applications.append(entry)

        return {
            "period": period.as_response(),
            "totals": totals,
            "previous": previous,
            "coverage": coverage,
            "applications": applications,
            "series": series,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        connection.close()


@router.get(
    "/errors",
    operation_id="get_stats_errors",
    response_model=StatsErrorsResponseModel,
)
def get_stats_errors(
    params: PeriodParams = Depends(period_params),
    username: str = RequireJWT,
):
    """Failed requests and degraded answers, from raw rows only (14-day retention)."""
    connection = create_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        db = PUBLIC_DB_NAME
        period = resolve_period(cursor, params)
        raw_from = fetch_raw_available_from(cursor, db)

        cursor.execute(f"""
            SELECT status_code, method, endpoint,
                   COUNT(*) AS `count`, MAX(created_at) AS last_seen
            FROM {db}.api_requests
            WHERE created_at >= %s AND created_at < %s AND status_code >= 400
            GROUP BY status_code, method, endpoint
            ORDER BY status_code >= 500 DESC, `count` DESC, last_seen DESC,
                     status_code, endpoint, method
            LIMIT %s
        """, (period.start, period.end, FAILURES_LIMIT))
        errors = cursor.fetchall()

        cursor.execute(f"""
            SELECT degraded_reason AS reason, endpoint,
                   COUNT(*) AS `count`, MAX(created_at) AS last_seen
            FROM {db}.api_requests
            WHERE created_at >= %s AND created_at < %s
              AND degraded_reason IS NOT NULL
            GROUP BY degraded_reason, endpoint
            ORDER BY `count` DESC, last_seen DESC, reason, endpoint
            LIMIT %s
        """, (period.start, period.end, FAILURES_LIMIT))
        degradations = cursor.fetchall()

        return {
            "period": period.as_response(),
            "raw_available_from": raw_from,
            "partial": raw_from is not None and period.start < raw_from,
            "errors": errors,
            "degradations": degradations,
        }

    except HTTPException:
        raise
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
                   client_ip AS client_pseudonym, user_agent, degraded_reason, created_at
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
