"""
CSV 내보내기 (감사 제출용)

- UTF-8 BOM을 붙여 Excel에서 한글이 깨지지 않게 한다
- 수식 주입(CSV injection) 방지: =, +, -, @, 탭, CR로 시작하는 값 앞에 ' 를 붙인다
"""
import csv
import io
from datetime import datetime
from typing import Iterable, Sequence
from urllib.parse import quote

from fastapi.responses import Response

_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _cell(value) -> str:
    if value is None:
        return ""
    if hasattr(value, "value"):  # Enum
        value = value.value
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, bool):
        return "Y" if value else "N"
    text = str(value)
    if text.startswith(_FORMULA_PREFIXES):
        return "'" + text
    return text


def csv_response(filename_prefix: str, headers: Sequence[str], rows: Iterable[Sequence]) -> Response:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(headers)
    for row in rows:
        writer.writerow([_cell(v) for v in row])
    filename = f"{filename_prefix}_{datetime.now():%Y%m%d_%H%M%S}.csv"
    return Response(
        content="﻿" + buffer.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )
