# Security policy

Resume Shortlister handles candidate data (resumes, contact details) and feeds
untrusted text to a language model, so security reports are welcome.

## Supported versions

| Version | Supported |
| --- | --- |
| 1.5.x | yes |
| < 1.5 | no: update with the install line |

## Reporting a vulnerability

Please **do not open a public issue**. Report it privately through GitHub:
open the repository's **Security** tab and choose **Report a vulnerability**.
Include the version, how to reproduce it and what an attacker gains.

You can expect an acknowledgement within a week. Fixes are released as a new
patch version, and you are credited in the release notes unless you prefer not
to be.

## What counts

Reports are especially useful about:

- **Resume content that steers its own evaluation**: text that changes a
  candidate's verdicts, scores or recommendation without being flagged as a
  prompt-injection risk.
- **Candidate data leaving the machine** other than the resume text sent to
  the configured chat model (the daily update check asks PyPI only for a
  version number), or being written somewhere other than the data home
  (`~/.resume-shortlister`) and the reports directory.
- **File access outside its limits**: the agent's `write_file` tool reaching
  outside the reports directory, or file tools reading through crafted paths.
- **The browser app answering anyone but its own page**: another website
  open in the browser, another host name pointing at this machine (DNS
  rebinding), or a request without the token created at each start reaching
  the API (`resume-shortlister web` listens on 127.0.0.1 only).
- **Keys** (API keys) appearing in logs, reports, stored answers, errors, the
  browser app's pages or any answer of its API (the setup page sends a key in;
  nothing sends one back), or the `.env` file being readable by other users.
- **The installers and the app's icon** running anything other than what they
  install, or the uninstallers deleting anything outside the app's own files.
- **Vulnerable dependencies** that are reachable from the tool.

Out of scope: ranking quality and model disagreement on borderline candidates
(see the README's Limitations), and problems that need an attacker who already
controls the machine or the `.env` file.
