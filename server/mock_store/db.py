import sys
from contextlib import contextmanager
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

_SHARED = Path(__file__).resolve().parent.parent / "shared"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from settings import settings


@contextmanager
def get_conn():
    # commits on clean exit, rolls back on exception
    with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
        yield conn