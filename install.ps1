# Install Resume Shortlister on Windows, with nothing installed beforehand. Paste this into
# PowerShell (or the Command Prompt):
#
#   powershell -ExecutionPolicy ByPass -c "irm https://raw.githubusercontent.com/Akshay-Jhijhautia/resume-shortlister/main/install.ps1 | iex"
#
# It installs uv (a small Python installer, into ~\.local\bin) unless you have it, lets uv
# fetch its own Python, installs Resume Shortlister as the `resume-shortlister` command,
# asks once for your OpenAI API key, and puts Resume Shortlister in the Start menu and on
# the desktop. No administrator rights, git or Python needed. Running it again upgrades to
# the newest version and keeps your key and data. To remove it: uninstall.ps1, next to this file.
#
# Settings (environment variables), for testing or another source:
#   RESUME_SHORTLISTER_PACKAGE   what to install (default: from PyPI, with every chat provider)
#   RESUME_SHORTLISTER_PYTHON    the Python version uv uses (default: 3.12)
#   RESUME_SHORTLISTER_HOME      the data folder, where the key is kept (default: ~\.resume-shortlister)
#
# Written for Windows PowerShell 5.1, which every Windows 10 and 11 has. Everything runs in a
# function: `irm | iex` runs this in your own PowerShell window, which `exit` would close.

function Install-ResumeShortlister {
    $package = if ($env:RESUME_SHORTLISTER_PACKAGE) { $env:RESUME_SHORTLISTER_PACKAGE } else { "resume-shortlister[anthropic,google,ollama]" }
    $python = if ($env:RESUME_SHORTLISTER_PYTHON) { $env:RESUME_SHORTLISTER_PYTHON } else { "3.12" }

    # 1. uv
    $found = Get-Command uv -ErrorAction SilentlyContinue
    if ($found) {
        $uv = $found.Source
    } else {
        Write-Host "Installing uv (the installer for Python apps)..."
        powershell -NoProfile -ExecutionPolicy ByPass -Command "irm https://astral.sh/uv/install.ps1 | iex" | Out-Null
        $binHome = if ($env:XDG_BIN_HOME) { $env:XDG_BIN_HOME } else { Join-Path $HOME ".local\bin" }
        $uv = Join-Path $binHome "uv.exe"
        if (-not (Test-Path $uv)) { throw "uv did not install; see https://docs.astral.sh/uv/ and run this again." }
    }

    # 2. Resume Shortlister, with its own Python (downloaded by uv when this computer lacks it)
    Write-Host "Installing Resume Shortlister (a minute or two the first time)..."
    $bin = (& $uv tool dir --bin).Trim()
    $env:Path = "$bin;$env:Path"
    & $uv tool install --upgrade --python $python $package
    if ($LASTEXITCODE -ne 0) { throw "Resume Shortlister did not install (see the messages above)." }
    & $uv tool update-shell *> $null  # adds the command's folder to your PATH for new windows
    $command = Join-Path $bin "resume-shortlister.exe"
    if (-not (Test-Path $command)) { throw "the resume-shortlister command was not installed." }
    Write-Host "Installed: $(& $command --version)"

    # 3. The API key, kept in the data folder the app reads (asked only when none is there).
    # A folder in your user profile is readable by you (and administrators) only.
    $dataHome = $env:RESUME_SHORTLISTER_HOME
    if (-not $dataHome) { $dataHome = $env:PROFILE_MATCH_HOME }
    if (-not $dataHome) {
        $dataHome = Join-Path $HOME ".resume-shortlister"
        $legacy = Join-Path $HOME ".profile-match"
        if ((Test-Path $legacy) -and -not (Test-Path $dataHome)) { $dataHome = $legacy }
    }
    $envFile = Join-Path $dataHome ".env"

    if ((Test-Path $envFile) -and (Select-String -Path $envFile -Pattern '^\s*(OPENAI|ANTHROPIC|GOOGLE|LLM)_API_KEY=.' -Quiet)) {
        Write-Host "Your API key is already set in $envFile."
    } elseif ([Environment]::UserInteractive -and -not [Console]::IsInputRedirected) {
        $secure = Read-Host -AsSecureString "Paste your OpenAI API key (hidden), or press Enter to skip"
        $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
        try { $key = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr).Trim() }
        finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr) }
        if ($key) {
            New-Item -ItemType Directory -Force -Path $dataHome | Out-Null
            # UTF-8 without a byte order mark (PowerShell 5.1 would add one, which hides the
            # first setting), on a line of its own.
            $utf8 = New-Object System.Text.UTF8Encoding $false
            $line = "OPENAI_API_KEY=$key`n"
            if ((Test-Path $envFile) -and (Get-Item $envFile).Length -gt 0 -and
                -not [IO.File]::ReadAllText($envFile).EndsWith("`n")) { $line = "`n$line" }
            [IO.File]::AppendAllText($envFile, $line, $utf8)
            Write-Host "Saved your key in $envFile (in your user folder, readable by you only)."
        } else {
            Write-Host "Skipped: the app asks for your key when it first starts, and lets you choose another provider."
        }
    } else {
        Write-Host "The app asks for your API key when it first starts."
    }

    # 4. The icon that opens the app: in the Start menu and on the desktop
    & $command launcher *> $null
    $madeIcon = $LASTEXITCODE -eq 0

    Write-Host ""
    if ($madeIcon) {
        Write-Host "Done. Open Resume Shortlister from the Start menu or the desktop."
    } else {
        Write-Host "Done."
    }
    Write-Host "Or, in a new PowerShell window: resume-shortlister open"
    Write-Host ""

    # Started now for the person at this computer.
    if ([Environment]::UserInteractive -and -not [Console]::IsInputRedirected) {
        Write-Host "Starting it now..."
        & $command open *> $null
    }
}

Install-ResumeShortlister
