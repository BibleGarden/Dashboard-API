"""Exercise the public-schema DDL only in a disposable MySQL schema."""

import os
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import mysql.connector


MIGRATION = Path(__file__).resolve().parents[1] / "migrations" / (
    "2026_09_27_130000_drop_public_voice_alignment_verse_id.sql"
)


def test_public_voice_alignment_verse_id_migration_is_rerunnable():
    schema = f"test_voice_alignment_{uuid4().hex}"
    connection = mysql.connector.connect(
        host=os.environ["DB_HOST"],
        port=int(os.environ["DB_PORT"]),
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        autocommit=True,
    )
    cursor = connection.cursor()
    try:
        cursor.execute(f"CREATE DATABASE `{schema}`")
        cursor.execute(f"""
            CREATE TABLE `{schema}`.voice_alignments (
                code INT PRIMARY KEY,
                voice INT NOT NULL,
                translation_verse INT NULL,
                book_number SMALLINT NOT NULL,
                chapter_number SMALLINT NOT NULL,
                verse_number SMALLINT NOT NULL,
                `begin` DECIMAL(10, 3) NOT NULL,
                `end` DECIMAL(10, 3) NOT NULL,
                INDEX voice_alignments_translation_verse_idx (translation_verse)
            )
        """)
        cursor.execute(f"""
            INSERT INTO `{schema}`.voice_alignments
                (code, voice, translation_verse, book_number, chapter_number,
                 verse_number, `begin`, `end`)
            VALUES (1, 7, 9, 1, 2, 3, 1.250, 2.750)
        """)

        sql = "\n".join(
            line for line in MIGRATION.read_text().splitlines()
            if not line.lstrip().startswith("--")
        ).replace("cep_public.", f"`{schema}`.")
        sql = sql.replace("table_schema = 'cep_public'", f"table_schema = '{schema}'")
        statements = [part.strip() for part in sql.split(";") if part.strip()]

        # Simulate interruption after the index DDL, then finish and rerun.
        for statement in statements[:4]:
            cursor.execute(statement)
        assert _exists(cursor, schema, "statistics", "index_name",
                       "voice_alignments_translation_verse_idx") is False
        assert _exists(cursor, schema, "columns", "column_name",
                       "translation_verse") is True

        for statement in statements[4:] + statements:
            cursor.execute(statement)
        assert _exists(cursor, schema, "statistics", "index_name",
                       "voice_alignments_translation_verse_idx") is False
        assert _exists(cursor, schema, "columns", "column_name",
                       "translation_verse") is False
        cursor.execute(f"""
            SELECT voice, book_number, chapter_number, verse_number, `begin`, `end`
            FROM `{schema}`.voice_alignments
        """)
        assert cursor.fetchone() == (7, 1, 2, 3, Decimal("1.250"), Decimal("2.750"))
    finally:
        cursor.execute(f"DROP DATABASE IF EXISTS `{schema}`")
        cursor.close()
        connection.close()


def _exists(cursor, schema, table, field, name):
    cursor.execute(
        f"SELECT COUNT(*) FROM information_schema.{table} "
        f"WHERE table_schema = %s AND table_name = 'voice_alignments' "
        f"AND {field} = %s",
        (schema, name),
    )
    return cursor.fetchone()[0] == 1
