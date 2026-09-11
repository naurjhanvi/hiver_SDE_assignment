"""Extract complete Twitter conversation components containing XboxSupport.

Usage:
    python extract_xbox_conversations.py dataset/twcs.csv dataset/xbox_conversations.csv

The extractor uses tweet IDs and reply-parent relationships rather than matching
the word "Xbox" in tweet text. The output keeps the original CSV schema and
contains every XboxSupport tweet plus all earlier messages needed to provide its
customer-side conversation context.
"""

from __future__ import annotations

import argparse
import csv
import sqlite3
import tempfile
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_csv", type=Path)
    parser.add_argument("output_csv", type=Path)
    return parser.parse_args()


def batched_insert(cursor: sqlite3.Cursor, statement: str, rows: list[tuple]) -> None:
    if rows:
        cursor.executemany(statement, rows)
        rows.clear()


def main() -> None:
    args = parse_args()
    if not args.input_csv.is_file():
        raise FileNotFoundError(f"Input file does not exist: {args.input_csv}")
    if args.input_csv.resolve() == args.output_csv.resolve():
        raise ValueError("Output path must differ from input path.")

    args.output_csv.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="xbox_conversation_graph_") as temp_dir:
        db_path = Path(temp_dir) / "graph.sqlite"
        connection = sqlite3.connect(db_path)
        connection.execute("PRAGMA journal_mode = OFF")
        connection.execute("PRAGMA synchronous = OFF")
        connection.execute("PRAGMA temp_store = FILE")
        connection.execute("CREATE TABLE edges (tweet_id TEXT PRIMARY KEY, parent_id TEXT)")
        connection.execute("CREATE TABLE seeds (tweet_id TEXT PRIMARY KEY)")

        edge_rows: list[tuple[str, str | None]] = []
        seed_rows: list[tuple[str]] = []
        input_rows = 0

        with args.input_csv.open("r", encoding="utf-8", newline="") as source:
            reader = csv.DictReader(source)
            required_columns = {"tweet_id", "author_id", "in_response_to_tweet_id"}
            missing_columns = required_columns - set(reader.fieldnames or [])
            if missing_columns:
                raise ValueError(f"Input CSV is missing columns: {sorted(missing_columns)}")

            for row in reader:
                tweet_id = row["tweet_id"].strip()
                parent_id = row["in_response_to_tweet_id"].strip() or None
                if not tweet_id:
                    continue
                edge_rows.append((tweet_id, parent_id))
                if row["author_id"].strip().casefold() == "xboxsupport":
                    seed_rows.append((tweet_id,))
                input_rows += 1

                if len(edge_rows) >= 50_000:
                    batched_insert(
                        connection.cursor(),
                        "INSERT OR IGNORE INTO edges (tweet_id, parent_id) VALUES (?, ?)",
                        edge_rows,
                    )
                    batched_insert(
                        connection.cursor(),
                        "INSERT OR IGNORE INTO seeds (tweet_id) VALUES (?)",
                        seed_rows,
                    )
                    connection.commit()

            batched_insert(
                connection.cursor(),
                "INSERT OR IGNORE INTO edges (tweet_id, parent_id) VALUES (?, ?)",
                edge_rows,
            )
            batched_insert(
                connection.cursor(),
                "INSERT OR IGNORE INTO seeds (tweet_id) VALUES (?)",
                seed_rows,
            )
            connection.commit()

        print(f"Indexed {input_rows:,} tweets.", flush=True)

        seed_count = connection.execute("SELECT COUNT(*) FROM seeds").fetchone()[0]
        if seed_count == 0:
            raise ValueError("No tweets authored by XboxSupport were found.")

        connection.execute("CREATE INDEX edges_parent_id_idx ON edges (parent_id)")
        connection.execute("CREATE TABLE selected (tweet_id TEXT PRIMARY KEY)")
        connection.execute(
            """
            INSERT INTO selected (tweet_id)
            WITH RECURSIVE connected(tweet_id) AS (
                SELECT tweet_id FROM seeds
                UNION
                SELECT edges.parent_id
                FROM edges JOIN connected ON edges.tweet_id = connected.tweet_id
                WHERE edges.parent_id IS NOT NULL
            )
            SELECT tweet_id FROM connected
            """
        )
        connection.commit()
        selected_count = connection.execute("SELECT COUNT(*) FROM selected").fetchone()[0]
        selected_ids = {row[0] for row in connection.execute("SELECT tweet_id FROM selected")}
        print(f"Selected {selected_count:,} XboxSupport tweets and prior-context tweets.", flush=True)

        output_rows = 0
        inbound_rows = 0
        xbox_rows = 0
        with args.input_csv.open("r", encoding="utf-8", newline="") as source, args.output_csv.open(
            "w", encoding="utf-8", newline=""
        ) as destination:
            reader = csv.DictReader(source)
            writer = csv.DictWriter(destination, fieldnames=reader.fieldnames)
            writer.writeheader()
            for row in reader:
                tweet_id = row["tweet_id"].strip()
                if tweet_id in selected_ids:
                    writer.writerow(row)
                    output_rows += 1
                    inbound_rows += row.get("inbound", "").strip().casefold() == "true"
                    xbox_rows += row["author_id"].strip().casefold() == "xboxsupport"

        connection.close()

    print(f"Scanned {input_rows:,} input rows.")
    print(f"Found {seed_count:,} XboxSupport tweets.")
    print(f"Selected {selected_count:,} connected tweet IDs.")
    print(f"Wrote {output_rows:,} rows to {args.output_csv}.")
    print(f"Output contains {inbound_rows:,} inbound customer tweets and {xbox_rows:,} XboxSupport tweets.")


if __name__ == "__main__":
    main()
