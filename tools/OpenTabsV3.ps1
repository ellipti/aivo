# OpenTabsV3.ps1 - Configurable Windows Terminal tab/pane launcher with validation, logs, workspaces, dry-run
[CmdletBinding()]
param(
  [string]$ConfigPath,
  [string]$Workspace,
  [string]$LogPath = "$env:TEMP\OpenTabsV3.log",
  [switch]$DryRun
)

function Write-Log {
  param([string]$Message, [string]$Level = "INFO")
  $ts = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
  $line = "[$ts] [$Level] $Message"
  try { Add-Content -Path $LogPath -Value $line -Encoding UTF8 } catch {}
  if ($Level -eq "ERROR") { Write-Error $Message } else { Write-Host $Message }
}

function Resolve-ConfigPath {
  param([string]$ConfigPath, [string]$Workspace)
  if ($ConfigPath) { return $ConfigPath }
  if (-not $Workspace) { throw "Та -ConfigPath эсвэл -Workspace хоёрын аль нэгийг заавал өгнө." }
  $cfgRoot = Join-Path -Path $PSScriptRoot -ChildPath 'tools'
  $cfgDir  = Join-Path -Path $cfgRoot -ChildPath 'configs'
  return (Join-Path -Path $cfgDir -ChildPath ("tabs.{0}.json" -f $Workspace))
}

function Test-CommandAvailable { param([string]$Name) return [bool](Get-Command $Name -ErrorAction SilentlyContinue) }

function Validate-Config {
  param($Config)
  if (-not $Config) { throw 'Config хоосон байна.' }
  if (-not $Config.PSObject.Properties.Name -contains 'tabs') { throw "Config-д 'tabs' массив байх ёстой." }
  if (-not ($Config.tabs -is [System.Collections.IEnumerable])) { throw "'tabs' нь массив байх ёстой." }
  if ($Config.tabs.Count -lt 1) { throw "'tabs' хоосон байна." }
  $validSplits = @('none','right','down')
  $i = 0
  foreach ($t in $Config.tabs) {
    $i++
    if (-not $t.shell)   { throw "tabs[$i]: 'shell' заавал." }
    if (-not $t.command) { throw "tabs[$i]: 'command' заавал." }
    if ($t.split -and ($validSplits -notcontains [string]$t.split)) {
      throw ("tabs[{0}]: 'split' {1} буруу. Зөв: {2}" -f $i, $t.split, ($validSplits -join ', '))
    }
  }
  return $true
}

function Build-WtSegments { param($Config)
  $segments = @()
  foreach ($t in $Config.tabs) {
    $shell = ([string]$t.shell).Trim().ToLower()
    $title = [string]($t.title | ForEach-Object { $_ })
    $cmd   = [string]($t.command | ForEach-Object { $_ })
    $split = if ($t.split) { [string]$t.split } else { 'none' }
    switch ($shell) {
      'powershell' { $shellCmd = "powershell -NoLogo -NoExit -Command `"$cmd`"" }
      'pwsh'       { $shellCmd = "pwsh -NoLogo -NoExit -Command `"$cmd`"" }
      'cmd'        { $shellCmd = "cmd /k `"$cmd`"" }
      'wsl'        { $shellCmd = "wsl `"$cmd`"" }
      default      { $shellCmd = "$($t.shell) $cmd" }
    }
    $seg = if ($split -eq 'none') { 'new-tab' } else { "split-pane -$split" }
    if ($title) { $seg += " --title `"$title`"" }
    $seg += " $shellCmd"
    $segments += $seg
  }
  if ($segments.Count -gt 0 -and $segments[0].StartsWith('split-pane')) { $segments[0] = 'new-tab powershell -NoLogo -NoExit' }
  return $segments
}

# ---- Exec ----
try { New-Item -Path (Split-Path $LogPath -Parent) -ItemType Directory -Force | Out-Null } catch {}
Write-Log '----- OpenTabsV3 эхэллээ -----'

try {
  $cfgPath = Resolve-ConfigPath -ConfigPath $ConfigPath -Workspace $Workspace
  if (-not (Test-Path $cfgPath)) { throw "Config олдсонгүй: $cfgPath" }
  Write-Log ("Config: {0}" -f $cfgPath)

  if (-not (Test-CommandAvailable -Name 'wt')) { throw 'wt.exe (Windows Terminal) олдсонгүй. Microsoft Store-оос Windows Terminal суулгана уу.' }

  $json = Get-Content $cfgPath -Raw
  try { $config = $json | ConvertFrom-Json -ErrorAction Stop } catch { throw "JSON буруу байна: $($_.Exception.Message)" }

  [void](Validate-Config -Config $config)
  $segments = Build-WtSegments -Config $config
  $wtCmd = 'wt ' + ($segments -join ' ; ')
  Write-Log ("Босгосон команд: {0}" -f $wtCmd)

  $elevate = $false
  if ($config.PSObject.Properties.Name -contains 'elevate_admin') { $elevate = [bool]$config.elevate_admin }

  if ($DryRun) {
    Write-Log 'DRY-RUN: Зөвхөн командыг харууллаа. Ажиллуулсангүй.'
    Write-Output $wtCmd
    exit 0
  }

  if ($elevate) {
    $args = $wtCmd.Substring(3)
    Write-Log 'Админ горимд эхлүүлж байна...'
    Start-Process wt.exe -Verb RunAs -ArgumentList $args | Out-Null
  }
  else {
    Write-Log 'Хэвийн горимд эхлүүлж байна...'
    Start-Process wt.exe -ArgumentList @('-w','new', ($segments -join ' ; ')) | Out-Null
  }

  Write-Log 'Амжилттай.'
}
catch {
  Write-Log ("Алдаа: {0}" -f $_.Exception.Message) 'ERROR'
  exit 1
}
finally { Write-Log '----- OpenTabsV3 дууслаа -----' }


