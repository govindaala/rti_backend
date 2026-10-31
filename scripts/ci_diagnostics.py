"""Emit timestamped, line-accurate GitHub Actions annotations from pytest JUnit XML.

Every traceback frame is annotated, so the failing assertion and application frames
are both visible. Full logs and JUnit XML are uploaded as workflow artifacts.
"""
from __future__ import annotations

import html
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
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


def traceback_locations(traceback: str) -> list[tuple[str, int]]:
    """Return all Python traceback source locations in displayed order."""
    locations: list[tuple[str, int]] = []
    seen: set[tuple[str, int]] = set()
    for line in traceback.splitlines():
        candidate = line.strip()
        for pattern in LOCATION_PATTERNS:
            match = pattern.search(candidate)
            if match:
                path = match.group(1)
                if path.startswith("file://"):
                    path = path[7:]
                location = (path, int(match.group(2)))
                if location not in seen:
                    seen.add(location)
                    locations.append(location)
                break
    return locations


def main() -> int:
    report = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("reports/junit.xml")
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    print(f"CI diagnostic timestamp (UTC): {now}")

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
        problem = case.find("failure")
        if problem is None:
            problem = case.find("error")
        if problem is None:
            continue

        failures += 1
        test_name = ".".join(
            part for part in (case.get("classname", ""), case.get("name", "")) if part
        )
        detail = "\n".join(
            part
            for part in (problem.get("message", ""), (problem.text or "").strip())
            if part
        )
        detail = html.unescape(detail)
        first_line = detail.splitlines()[0][:500] if detail else "No failure message recorded"
        locations = traceback_locations(detail)

        print(f"\nFAILED TEST: {test_name}")
        print(f"FAILURE REASON: {first_line}")
        if locations:
            print("TRACEBACK SOURCE LOCATIONS (all frames, in traceback order):")
            for index, (path, line) in enumerate(locations, start=1):
                role = "test/assertion frame" if "/tests/" in f"/{path}" else "application frame"
                print(f"  {index}. {path}:{line} [{role}]")
                print(
                    f"::error file={command_escape(path)},line={line},"
                    f"title=Pytest failure ({index})::{command_escape(test_name + ': ' + first_line)}"
                )
            print(
                "ROOT-CAUSE REVIEW: inspect the final application frame above, "
                "then the assertion frame; the complete traceback follows."
            )
        else:
            print("SOURCE LOCATION: pytest did not provide a parseable Python file/line.")
            print(f"::error title=Pytest failure::{command_escape(test_name + ': ' + first_line)}")
        print("FULL FAILURE TRACEBACK:")
        print(detail[:20000])

    skipped = sum(1 for _ in root.iter("skipped"))
    print(
        f"CI diagnostic result at {now}: {failures} failed/error test(s), "
        f"{skipped} skipped test(s)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
