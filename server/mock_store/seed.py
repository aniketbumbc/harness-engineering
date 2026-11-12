from pathlib import Path

try:
    from .db import get_conn
except ImportError:
    from db import get_conn

HERE = Path(__file__).parent


def run():
    with get_conn() as conn:
        conn.execute((HERE / "schema.sql").read_text())
        conn.execute((HERE / "seed.sql").read_text())


if __name__ == "__main__":
    run()
    print("Mock store schema created and seeded.")