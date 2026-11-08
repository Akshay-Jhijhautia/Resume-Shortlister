"""The documentation stays true: its graph diagram is the compiled graph, and its links resolve."""

import re
import zipfile

import pytest

import matching_agent
from resume_shortlister import __version__
from scripts import ci_failures, pypi_readme, release_notes, sample_kit
from tests.fakes import FakeChatModel
from tests.paths import ROOT

# "a --> b" and "a -.->|label| b", with node shapes such as "__end__([END])" allowed.
EDGE_RE = re.compile(r"^\s*(\w+)(?:\(\[\w+\]\))?\s*-\.?->\s*(?:\|[^|]*\|\s*)?(\w+)", re.MULTILINE)
LINK_RE = re.compile(r"\]\(([^)\s]+)\)")
CODE_RE = re.compile(r"^```.*?^```", re.MULTILINE | re.DOTALL)
DOCS = ["README.md", "CHANGELOG.md", "SECURITY.md", "frontend/README.md", *sorted(
    p.relative_to(ROOT).as_posix() for p in (ROOT / "docs").glob("*.md"))]


def test_the_documented_diagram_matches_the_compiled_graph(services):
    guide = (ROOT / "docs" / "how-it-works.md").read_text(encoding="utf-8")
    diagram = guide.split("```mermaid", 1)[1].split("```", 1)[0]
    documented = set(EDGE_RE.findall(diagram))

    services.model = FakeChatModel({})
    graph = matching_agent.build_graph(services, conversational=True).get_graph()
    actual = {(edge.source, edge.target) for edge in graph.edges}
    assert documented == actual


def _anchors(markdown: str) -> set[str]:
    """Heading anchors as GitHub makes them: lower case, punctuation dropped, spaces as hyphens."""
    headings = re.findall(r"^#+ (.+)$", CODE_RE.sub("", markdown), re.MULTILINE)
    return {re.sub(r"[^\w\- ]", "", h.strip().lower()).replace(" ", "-") for h in headings}


def test_every_link_between_the_docs_resolves():
    broken = []
    for doc in DOCS:
        source = ROOT / doc
        for link in LINK_RE.findall(CODE_RE.sub("", source.read_text(encoding="utf-8"))):
            if re.match(r"[a-z]+:", link):  # https:, mailto:
                continue
            path, _, anchor = link.partition("#")
            target = (source.parent / path).resolve() if path else source
            if not target.exists():
                broken.append(f"{doc}: {link} (no such file)")
            elif anchor and target.suffix == ".md" and anchor not in _anchors(target.read_text(encoding="utf-8")):
                broken.append(f"{doc}: {link} (no such heading)")
    assert broken == []


def test_the_pypi_readme_links_every_file_on_github_at_the_release_tag():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    repo = pypi_readme.repository_url()
    published = pypi_readme.absolute_links(readme, "v9.9.9", repo)

    links = LINK_RE.findall(published)
    assert links and all(re.match(r"https:", link) for link in links)
    assert f"]({repo}/blob/v9.9.9/LICENSE)" in published
    assert f"]({repo}/blob/v9.9.9/README.md#limitations)" in published
    raw = repo.replace("https://github.com/", "https://raw.githubusercontent.com/")
    assert f"]({raw}/v9.9.9/docs/images/resume-shortlister-demo.gif)" in published
    assert LINK_RE.sub("", published) == LINK_RE.sub("", readme)  # only the links changed


def test_ci_failures_become_annotations(tmp_path):
    report = tmp_path / "results.xml"
    report.write_text(
        '<testsuites><testsuite><testcase classname="tests.test_pools" name="test_split[a,b]">'
        '<failure message="assert 1 == 2&#10;50% done: C:\\x">trace</failure></testcase>'
        '<testcase classname="tests.test_ok" name="test_fine"/></testsuite></testsuites>', encoding="utf-8")
    assert ci_failures.annotations(str(report)) == [
        "::error title=tests.test_pools.test_split[a%2Cb]::assert 1 == 2%0A50%25 done: C:\\x"]


def test_the_release_notes_are_the_versions_changelog_section():
    changelog = "# Changelog\n\n## 1.5.1 (2026-11-05)\n\nFixes.\n\n### Fixed\n\n- A thing.\n\n## 1.5.0 (2026-11-04)\n\nOlder.\n"
    text = release_notes.notes("1.5.1", changelog)
    assert text.startswith("Fixes.\n\n### Fixed\n\n- A thing.\n") and "Older." not in text
    assert "install.ps1 | iex" in text and "install.sh | sh" in text and "sample-resumes.zip" in text
    with pytest.raises(ValueError, match="no section for 9.9.9"):
        release_notes.notes("9.9.9", changelog)
    assert release_notes.notes(__version__, (ROOT / "CHANGELOG.md").read_text(encoding="utf-8"))  # this version has one


def test_the_sample_kit_has_resumes_job_descriptions_and_a_guide(tmp_path):
    archive = sample_kit.build(tmp_path / "kit.zip", count=12)
    with zipfile.ZipFile(archive) as kit:
        names = kit.namelist()
        assert "resume-shortlister-samples/README.txt" in names
        assert "made up" in kit.read("resume-shortlister-samples/README.txt").decode("utf-8")
    assert sum(name.startswith("resume-shortlister-samples/resumes/") for name in names) == 12
    assert {name.rsplit("/", 1)[1] for name in names if "/job-descriptions/" in name} == set(sample_kit.ROLES.values())


CONFLICT_RE = re.compile(r"^(<<<<<<<|=======|>>>>>>>)( |$)", re.MULTILINE)
TEXT_SUFFIXES = {".py", ".md", ".yml", ".yaml", ".toml", ".json", ".sh", ".ps1", ".ts", ".tsx", ".css", ".html", ".txt"}
SKIPPED_DIRS = {".git", ".venv", "node_modules", "build", "dist", "__pycache__", ".pytest_cache"}


def test_no_file_holds_merge_conflict_markers():
    """A conflict left in a file (from a merge, or a stash popped onto another branch) breaks
    it: a workflow GitHub cannot read, a heading in the changelog."""
    left = []
    for path in ROOT.rglob("*"):
        if path.suffix in TEXT_SUFFIXES and path.is_file() and not SKIPPED_DIRS & set(path.relative_to(ROOT).parts):
            text = path.read_text(encoding="utf-8", errors="replace")
            left += [f"{path.relative_to(ROOT)}:{text[:m.start()].count(chr(10)) + 1}" for m in CONFLICT_RE.finditer(text)]
    assert left == []
