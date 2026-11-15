import sys
from pathlib import Path

from .db import get_conn

SCHEMA = Path(__file__).parent / "schema.sql"


def run(reset: bool = False):
    with get_conn() as conn:
        if reset:
            conn.execute("DROP SCHEMA IF EXISTS harness CASCADE")
        conn.execute(SCHEMA.read_text())


if __name__ == "__main__":
    run(reset="--reset" in sys.argv)
    print("harness schema ready")