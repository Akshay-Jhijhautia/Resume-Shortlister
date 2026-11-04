# Remove Resume Shortlister from Windows. Paste this into PowerShell:
#
#   powershell -ExecutionPolicy ByPass -c "irm https://raw.githubusercontent.com/Akshay-Jhijhautia/resume-shortlister/main/uninstall.ps1 | iex"
#
# It stops the app (Windows cannot remove a program that is running), removes its Start
# menu and desktop shortcuts and the resume-shortlister command, and asks before deleting
# your data (screenings, indexes, uploaded copies, your key, the language model). uv, which
# the installer brought, stays: other programs may use it.
#
# Everything runs in a function: `irm | iex` runs this in your own PowerShell window, which
# `exit` would close.

function Uninstall-ResumeShortlister {
    $binHome = if ($env:XDG_BIN_HOME) { $env:XDG_BIN_HOME } else { Join-Path $HOME ".local\bin" }
    $found = Get-Command resume-shortlister -ErrorAction SilentlyContinue
    $command = if ($found) { $found.Source } else { Join-Path $binHome "resume-shortlister.exe" }
    $foundUv = Get-Command uv -ErrorAction SilentlyContinue
    $uv = if ($foundUv) { $foundUv.Source } else { Join-Path $binHome "uv.exe" }

    # 1. The app and its shortcuts
    if (Test-Path $command) {
        & $command stop
        & $command launcher --remove
    }

    # 2. The command
    $installed = (Test-Path $uv) -and ((& $uv tool list 2>$null) -match '^resume-shortlister ')
    if ($installed) {
        & $uv tool uninstall resume-shortlister
        if ($LASTEXITCODE -ne 0) { throw "The command could not be removed: is Resume Shortlister still open? Quit it and run this again." }
        Write-Host "Removed the resume-shortlister command."
    } else {
        Write-Host "The resume-shortlister command was not installed with uv; if you installed it with pip, run: pip uninstall resume-shortlister"
    }

    # 3. Your data, only when you say so, and only the app's own folder
    $dataHome = $env:RESUME_SHORTLISTER_HOME
    if (-not $dataHome) { $dataHome = $env:PROFILE_MATCH_HOME }
    if (-not $dataHome) {
        $dataHome = Join-Path $HOME ".resume-shortlister"
        $legacy = Join-Path $HOME ".profile-match"
        if ((Test-Path $legacy) -and -not (Test-Path $dataHome)) { $dataHome = $legacy }
    }
    if (Test-Path $dataHome) {
        $ours = @(".resume-shortlister", ".profile-match") -contains (Split-Path $dataHome -Leaf)
        $answer = ""
        if ($ours -and [Environment]::UserInteractive -and -not [Console]::IsInputRedirected) {
            $answer = Read-Host "Also delete your data in $dataHome (screenings, indexes, uploaded copies, your key, the language model)? [y/N]"
        }
        if ($answer -match '^(y|yes)$') {
            Remove-Item -Recurse -Force $dataHome
            Write-Host "Deleted $dataHome."
        } else {
            Write-Host "Kept your data in $dataHome; delete that folder to remove it."
        }
    }

    Write-Host "Done. uv stays installed; to remove it too, see https://docs.astral.sh/uv/getting-started/installation/#uninstallation"
}

Uninstall-ResumeShortlister
