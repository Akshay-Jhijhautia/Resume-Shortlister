"""Print each failed test of a JUnit XML report as a GitHub Actions error annotation.

Annotations show on the run's summary page (and through the public API), so a failure
on one system can be read without opening, or having access to, the full log.

    pytest --junitxml=test-results.xml || python -m scripts.ci_failures test-results.xml
"""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET

MAX_MESSAGE = 900  # GitHub shows the start of long annotations; the rest is in the log


def annotations(report: str) -> list[str]:
    lines = []
    for case in ET.parse(report).iter("testcase"):
        for problem in case:
            if problem.tag in ("failure", "error"):
                message = (problem.get("message") or problem.text or "")[:MAX_MESSAGE]
                title = f"{case.get('classname')}.{case.get('name')}"
                lines.append(f"::error title={_escape(title, property=True)}::{_escape(message)}")
    return lines


def _escape(text: str, property: bool = False) -> str:
    """Workflow-command escaping: the message keeps its line breaks; a title has no ":" or ","."""
    text = text.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    return text.replace(":", "%3A").replace(",", "%2C") if property else text


def main(argv: list[str] | None = None) -> None:
    args = sys.argv[1:] if argv is None else argv
    for line in annotations(args[0] if args else "test-results.xml"):
        print(line)


if __name__ == "__main__":
    main()
