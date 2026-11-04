"""The sample kit: fictional resumes and job descriptions to try the app with, as a zip.

Every GitHub release attaches it (see .github/workflows/release.yml), so anyone
can try Resume Shortlister in minutes without real candidates' resumes. The
resumes are made up (``generate_sample_resumes``), names and contact details
included.

    python -m scripts.sample_kit dist/resume-shortlister-sample-resumes.zip
"""

from __future__ import annotations

import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

from scripts import generate_sample_resumes

ROOT = Path(__file__).resolve().parent.parent
JOB_DESCRIPTIONS = ROOT / "tests" / "fixtures" / "job_descriptions"
# The roles the sample resumes are written for, each with a good number of fits.
ROLES = {"frontend_react.txt": "frontend-developer.txt", "senior_python_ml.txt": "python-ml-engineer.txt",
         "devops_sre.txt": "devops-engineer.txt"}
GUIDE = """Resume Shortlister: sample resumes to try it with
==================================================

Everything here is made up: 100 fictional resumes (PDF, DOCX and TXT) and three
job descriptions. The people, companies and contact details do not exist.

To try it:
1. Unzip this file.
2. Open Resume Shortlister and paste the path of the "resumes" folder in
   "Or a folder on this computer", then click Load (or drop some of the files
   on the page).
3. Open a job description from "job-descriptions", copy all of it, paste it
   into the Role box and click "Screen resumes".
4. Open a candidate for the evidence behind their place.
"""


def build(target: Path, count: int = generate_sample_resumes.DEFAULT_COUNT) -> Path:
    """Write the kit's zip to ``target``."""
    with tempfile.TemporaryDirectory() as work:
        kit = Path(work) / "resume-shortlister-samples"
        generate_sample_resumes.main([str(kit / "resumes"), "--count", str(count)])
        (kit / "job-descriptions").mkdir()
        for source, name in ROLES.items():
            shutil.copyfile(JOB_DESCRIPTIONS / source, kit / "job-descriptions" / name)
        (kit / "README.txt").write_text(GUIDE, encoding="utf-8")
        target.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(kit.rglob("*")):
                if path.is_file():
                    archive.write(path, path.relative_to(kit.parent).as_posix())
    return target


def main(argv: list[str] | None = None) -> None:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        sys.exit("usage: python -m scripts.sample_kit <zip file to write>")
    target = build(Path(args[0]))
    print(f"Wrote {target} ({target.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
