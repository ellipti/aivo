param(
  [string]$ConfigPath = ".\tools\tabs.json"
)

if (-not (Test-Path $ConfigPath)) {
  Write-Error "Config not found: $ConfigPath"
  exit 1
}

# JSON унших
$configRaw = Get-Content $ConfigPath -Raw
try {
  $config = $configRaw | ConvertFrom-Json -ErrorAction Stop
} catch {
  Write-Error "Invalid JSON in $ConfigPath: $($_.Exception.Message)"
  exit 1
}

# wt.exe байгаа эсэхийг шалгах
$wt = Get-Command wt -ErrorAction SilentlyContinue
if (-not $wt) {
  Write-Error "wt.exe (Windows Terminal) олдсонгүй. Microsoft Store-оос суулгаарай."
  exit 1
}

# Admin горим
$elevate = $false
if ($config.PSObject.Properties.Name -contains 'elevate_admin') {
  $elevate = [bool]$config.elevate_admin
}

# Таб нээх командын буфер
$segments = @()

foreach ($t in $config.tabs) {
  $shell = if ($t.shell) { [string]$t.shell } else { 'powershell' }
  $title = if ($t.title) { [string]$t.title } else { '' }
  $cmd   = if ($t.command) { [string]$t.command } else { '' }
  $split = if ($t.split) { [string]$t.split } else { 'none' }

  switch -Regex ($shell.ToLower()) {
    'powershell' { $shellCmd = "powershell -NoLogo -NoExit -Command `"$cmd`"" }
    'pwsh'       { $shellCmd = "pwsh -NoLogo -NoExit -Command `"$cmd`"" }
    'cmd'        { $shellCmd = "cmd /k `"$cmd`"" }
    default      { $shellCmd = "$shell $cmd" }
  }

  if ($split -eq 'none') {
    $seg = 'new-tab'
  } else {
    $seg = "split-pane -$split"
  }

  if ($title -ne '') { $seg += " --title `"$title`"" }
  $seg += " $shellCmd"
  $segments += $seg
}

# Эхний сегмент split-ээр эхэлбэл new-tab болгох
if ($segments.Count -gt 0 -and $segments[0] -like 'split*') {
  $segments[0] = 'new-tab powershell -NoLogo -NoExit'
}

$joined = ($segments -join ' ; ')
$argList = @()
$argList += '-w'
$argList += 'new'
$argList += $joined

if ($elevate) {
  Start-Process wt.exe -Verb RunAs -ArgumentList $argList
} else {
  Start-Process wt.exe -ArgumentList $argList | Out-Null
}


