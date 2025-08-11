# Нэг командоор Windows Terminal-д тусдаа табууд нээх скрипт.
# Fallback: Windows Terminal байхгүй үед тусдаа PowerShell цонх бүр нээнэ.

$ErrorActionPreference = 'Stop'

$tabs = @(
  @{ Title = 'Web';      Path = 'D:\AIVO';                   Command = 'pnpm --filter web dev' }
  @{ Title = 'Analyzer'; Path = 'D:\AIVO\services\analyzer'; Command = 'python main.py' }
  @{ Title = 'Executor'; Path = 'D:\AIVO\services\executor'; Command = 'python main.py' }
  @{ Title = 'Docker';   Path = 'D:\AIVO';                   Command = 'docker compose up' }
)

$wt = Get-Command wt.exe -ErrorAction SilentlyContinue

if ($wt) {
  # Windows Terminal: нэг цонхонд олон таб нээх
  $sub = $tabs | ForEach-Object {
    $title = $_.Title
    $path  = $_.Path
    $cmd   = $_.Command
    "new-tab --title `"$title`" powershell -NoLogo -NoExit -Command `"cd `"$path`"; $cmd`""
  }

  $args = @('-w','new', ($sub -join ' ; '))
  Start-Process -FilePath 'wt.exe' -ArgumentList $args | Out-Null
}
else {
  # Fallback: тус тусдаа PowerShell цонх
  foreach ($t in $tabs) {
    $psArgs = @(
      '-NoLogo','-NoExit','-Command',
      "cd `"$($t.Path)`"; $($t.Command)"
    )
    Start-Process -FilePath 'powershell.exe' -ArgumentList $psArgs | Out-Null
  }
}


