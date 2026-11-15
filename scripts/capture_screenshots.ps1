$ErrorActionPreference = "Stop"

$chrome = "C:\Program Files\Google\Chrome\Application\chrome.exe"
if (-not (Test-Path $chrome)) {
    Write-Error "Chrome executable not found at $chrome"
}

$outputDir = "C:\Users\mrksp\CampusQueri\app\static\img"
if (-not (Test-Path $outputDir)) {
    New-Item -ItemType Directory -Force -Path $outputDir | Out-Null
}

$targets = @(
    @{ Name = "screenshot_desktop_home.png"; Url = "http://127.0.0.1:5000/"; Size = "1440,900" },
    @{ Name = "screenshot_mobile_home.png"; Url = "http://127.0.0.1:5000/"; Size = "390,844" },
    @{ Name = "screenshot_desktop_notices.png"; Url = "http://127.0.0.1:5000/notices"; Size = "1440,900" },
    @{ Name = "screenshot_desktop_offices.png"; Url = "http://127.0.0.1:5000/offices"; Size = "1440,900" },
    @{ Name = "screenshot_desktop_assistant.png"; Url = "http://127.0.0.1:5000/assistant"; Size = "1440,900" },
    @{ Name = "screenshot_desktop_login.png"; Url = "http://127.0.0.1:5000/auth/login"; Size = "1440,900" },
    @{ Name = "screenshot_desktop_register.png"; Url = "http://127.0.0.1:5000/auth/register"; Size = "1440,900" },
    @{ Name = "screenshot_mobile_notices.png"; Url = "http://127.0.0.1:5000/notices"; Size = "390,844" }
)

foreach ($t in $targets) {
    $outPath = Join-Path $outputDir $t.Name
    Write-Host "Capturing $($t.Name) ($($t.Size)) from $($t.Url) ..."
    $args = @(
        "--headless=new",
        "--disable-gpu",
        "--hide-scrollbars",
        "--window-size=$($t.Size)",
        "--screenshot=$outPath",
        $t.Url
    )
    $proc = Start-Process -FilePath $chrome -ArgumentList $args -Wait -PassThru
    if (Test-Path $outPath) {
        $fileInfo = Get-Item $outPath
        Write-Host "  -> Success: $outPath ($($fileInfo.Length) bytes)"
    } else {
        Write-Warning "  -> Failed to create screenshot for $($t.Name)"
    }
}
