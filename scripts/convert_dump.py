"""
SQLite to MySQL Dump Converter
Converts dump.sql (SQLite format) to mysql_dump.sql (MySQL format)
"""

import re
import sys

INPUT_FILE = r"c:\PATIENTPATH-AI\dump_utf8.sql"
OUTPUT_FILE = r"c:\PATIENTPATH-AI\backend\mysql_dump.sql"


def convert_sqlite_to_mysql(input_path, output_path):
    with open(input_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    output_lines = []
    output_lines.append("-- ============================================================\n")
    output_lines.append("-- PatientPath AI - MySQL Data Import\n")
    output_lines.append("-- ============================================================\n")
    output_lines.append("-- Converted from SQLite dump.sql\n")
    output_lines.append("-- Usage: mysql -u root -p patientpath < mysql_dump.sql\n")
    output_lines.append("-- ============================================================\n\n")
    output_lines.append("SET NAMES utf8mb4;\n")
    output_lines.append("SET FOREIGN_KEY_CHECKS = 0;\n")
    output_lines.append("SET SQL_MODE = 'NO_AUTO_VALUE_ON_ZERO';\n\n")

    skip_lines = {"PRAGMA", "BEGIN TRANSACTION", "COMMIT", "DELETE FROM sqlite"}
    in_create = False
    create_buffer = []

    for line in lines:
        stripped = line.strip()

        # Skip empty lines and SQLite-specific commands
        if not stripped:
            continue
        if any(stripped.upper().startswith(s) for s in skip_lines):
            continue

        # Handle CREATE TABLE
        if stripped.upper().startswith("CREATE TABLE"):
            in_create = True
            create_buffer = [line]
            continue

        if in_create:
            create_buffer.append(line)
            if ");" in stripped:
                in_create = False
                table_sql = "".join(create_buffer)
                mysql_table = convert_create_table(table_sql)
                output_lines.append(mysql_table)
                output_lines.append("\n")
                create_buffer = []
            continue

        # Handle CREATE INDEX
        if stripped.upper().startswith("CREATE INDEX") or stripped.upper().startswith("CREATE UNIQUE INDEX"):
            mysql_idx = convert_create_index(stripped)
            if mysql_idx:
                output_lines.append(mysql_idx + "\n")
            continue

        # Handle INSERT statements
        if stripped.upper().startswith("INSERT INTO"):
            output_lines.append(stripped + "\n")
            continue

    output_lines.append("\nSET FOREIGN_KEY_CHECKS = 1;\n")

    with open(output_path, "w", encoding="utf-8") as f:
        f.writelines(output_lines)

    print(f"Conversion complete: {output_path}")
    print(f"Total lines written: {len(output_lines)}")


def convert_create_table(sql):
    """Convert SQLite CREATE TABLE to MySQL format."""
    # Replace AUTOINCREMENT with AUTO_INCREMENT
    sql = sql.replace("AUTOINCREMENT", "AUTO_INCREMENT")

    # Replace BOOLEAN with TINYINT(1)
    sql = re.sub(r'\bBOOLEAN\b', 'TINYINT(1)', sql, flags=re.IGNORECASE)

    # Add IF NOT EXISTS
    sql = sql.replace("CREATE TABLE ", "CREATE TABLE IF NOT EXISTS ", 1)

    # Add ENGINE and CHARSET at the end
    sql = sql.rstrip().rstrip(";")
    sql += " ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;\n"

    return sql


def convert_create_index(sql):
    """Convert SQLite CREATE INDEX to MySQL format."""
    # MySQL handles indexes differently, but basic CREATE INDEX is compatible
    # Just make sure to handle IF NOT EXISTS
    return sql


if __name__ == "__main__":
    convert_sqlite_to_mysql(INPUT_FILE, OUTPUT_FILE)
