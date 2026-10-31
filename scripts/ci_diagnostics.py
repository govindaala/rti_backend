"""Turn pytest JUnit failures into precise GitHub Actions annotations.

The original pytest log remains available as a CI artifact. This helper extracts
the first useful source location from each failed test's traceback.
"""
from __future__ import annotations

import html
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

LOCATION_PATTERNS = (
    re.compile(r'File "([^"]+)", line (\d+)'),
    re.compile(r"([\w./-]+\.py):(\d+)(?::\d+)?(?:: in .*)?$"),
)


def command_escape(value: str) -> str:
    """Escape values for GitHub workflow command properties/messages."""
    return (
        value.replace("%", "%25")
        .replace("\r", "%0D")
        .replace("\n", "%0A")
        .replace(":", "%3A")
        .replace(",", "%2C")
    )


def first_location(traceback: str) -> tuple[str, int] | None:
    for line in reversed(traceback.splitlines()):
        candidate = line.strip()
        for pattern in LOCATION_PATTERNS:
            match = pattern.search(candidate)
            if match:
                path = match.group(1)
                if path.startswith("file://"):
                    path = path[7:]
                return path, int(match.group(2))
    return None


def main() -> int:
    report = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("reports/junit.xml")
    if not report.exists():
        print(f"::warning::JUnit report not found: {report}")
        return 0

    try:
        root = ET.parse(report).getroot()
    except (ET.ParseError, OSError) as exc:
        print(f"::error title=CI diagnostics parser::{command_escape(str(exc))}")
        return 1

    failures = 0
    for case in root.iter("testcase"):
        failure = case.find("failure")
        error = case.find("error")
        problem = failure if failure is not None else error
        if problem is None:
            continue

        failures += 1
        test_name = ".".join(
            part for part in (case.get("classname", ""), case.get("name", "")) if part
        )
        detail = "\\n".join(
            part for part in (problem.get("message", ""), (problem.text or "").strip()) if part
        )
        detail = html.unescape(detail)
        location = first_location(detail)

        if location:
            path, line = location
            message = f"{test_name}: {detail.splitlines()[0][:500]}"
            print(
                f"::error file={command_escape(path)},line={line},"
                f"title=Pytest failure::{command_escape(message)}"
            )
        else:
            message = f"{test_name}: {detail.splitlines()[0][:500]}"
            print(f"::error title=Pytest failure::{command_escape(message)}")

        print(f"Failed test: {test_name}")
        if detail:
            print(detail[:12000])

    skipped = sum(1 for _ in root.iter("skipped"))
    print(
        f"CI diagnostic result: {failures} failed/error test(s), "
        f"{skipped} skipped test(s)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
