$ErrorActionPreference = 'Stop'
$OUT = "AIVO_AUDIT.md"
Remove-Item $OUT -ErrorAction SilentlyContinue

Add-Content $OUT "# AIVO Audit Bundle ($(Get-Date -Format u))`n"

# Versions
Add-Content $OUT "## Versions`n```"
Add-Content $OUT ("Node: " + (node -v))
Add-Content $OUT ("pnpm: " + (pnpm -v))
$pyVer = try { (py -3 --version) } catch { (python --version) }
Add-Content $OUT ("Python: " + $pyVer)
Add-Content $OUT "````n"

# Last commit
Add-Content $OUT "## Last Commit`n```"
(git log -1 --stat | Out-String) | Add-Content $OUT
Add-Content $OUT "````n"

# Curated file list (exclude heavy dirs)
Add-Content $OUT "## File List (curated, excluding node_modules/.next/.turbo/.git)__`n```"
Get-ChildItem -Recurse -File |
  Where-Object { $_.FullName -notmatch '\\(node_modules|\.next|\.turbo|__pycache__|\.venv|build|dist|\.git)\\' } |
  ForEach-Object { $_.FullName.Substring($pwd.Path.Length+1) } |
  Sort-Object | Out-String | Add-Content $OUT
Add-Content $OUT "````n"

function Add-FileBlock([string]$path) {
  if (Test-Path $path) {
    Add-Content $OUT "`n### $path`n```"
    (Get-Content $path -Raw) | Add-Content $OUT
    Add-Content $OUT "````n"
  }
}

# Root configs
Add-Content $OUT "## Root Configs"
Add-FileBlock "package.json"
Add-FileBlock "turbo.json"
Add-FileBlock "docker-compose.yml"

# Web (apps/web) – key pages & API proxies
Add-Content $OUT "## apps/web key files"
Add-FileBlock "apps/web/app/page.tsx"
Add-FileBlock "apps/web/app/login/page.tsx"
Add-FileBlock "apps/web/app/dashboard/page.tsx"
Add-FileBlock "apps/web/app/analyze/page.tsx"
Add-FileBlock "apps/web/components/WorldMapHero.tsx"
Add-FileBlock "apps/web/components/DecisionCard.tsx"
Add-FileBlock "apps/web/app/api/analyze/route.ts"
Add-FileBlock "apps/web/app/api/orders/route.ts"
Add-FileBlock "apps/web/.env.local.example"

# Admin (apps/admin)
Add-Content $OUT "## apps/admin key files"
Add-FileBlock "apps/admin/app/dashboard/page.tsx"
Add-FileBlock "apps/admin/app/settings/page.tsx"
Add-FileBlock "apps/admin/.env.local.example"

# Analyzer service
Add-Content $OUT "## services/analyzer"
Add-FileBlock "services/analyzer/main.py"
Add-FileBlock "services/analyzer/requirements.txt"
Add-FileBlock "services/analyzer/.env.example"

# Executor service
Add-Content $OUT "## services/executor"
Add-FileBlock "services/executor/main.py"
Add-FileBlock "services/executor/requirements.txt"
Add-FileBlock "services/executor/.env.example"

# Health checks
Add-Content $OUT "## Health Checks`n```"
try { Add-Content $OUT ("analyzer /health -> " + (Invoke-WebRequest http://localhost:7001/health -UseBasicParsing).Content) } catch { Add-Content $OUT ("analyzer /health error -> " + $_.Exception.Message) }
try { Add-Content $OUT ("executor /health -> " + (Invoke-WebRequest http://localhost:7002/health -UseBasicParsing).Content) } catch { Add-Content $OUT ("executor /health error -> " + $_.Exception.Message) }
Add-Content $OUT "```"

Write-Host "`nGenerated: $OUT"
 = "AIVO_AUDIT.md"
Remove-Item  -ErrorAction SilentlyContinue

Add-Content  "# AIVO Audit Bundle (2025-08-11 08:53:30Z)
"

# Versions
Add-Content  "## Versions
`"
Add-Content  ("Node: " + (node -v))
Add-Content  ("pnpm: " + (pnpm -v))
Add-Content  ("Python: " + ((py -3 --version) 2> ?? (python --version)))
Add-Content  "``n"

# Last commit
Add-Content  "## Last Commit
`"
(git log -1 --stat | Out-String) | Add-Content 
Add-Content  "``n"

# Curated file list (exclude heavy dirs)
Add-Content  "## File List (curated, excluding node_modules/.next/.turbo/.git)__
`"
Get-ChildItem -Recurse -File |
  Where-Object { .FullName -notmatch '\\(node_modules|\.next|\.turbo|__pycache__|\.venv|build|dist|\.git)\\' } |
  ForEach-Object { .FullName.Substring(D:\AIVO.Path.Length+1) } |
  Sort-Object | Out-String | Add-Content 
Add-Content  "``n"

function Add-FileBlock([string]) {
  if (Test-Path ) {
    Add-Content  "
### 
`"
    (Get-Content  -Raw) | Add-Content 
    Add-Content  "``n"
  }
}

# Root configs
Add-Content  "## Root Configs"
Add-FileBlock "package.json"
Add-FileBlock "turbo.json"
Add-FileBlock "docker-compose.yml"

# Web (apps/web)  key pages & API proxies
Add-Content  "## apps/web key files"
Add-FileBlock "apps/web/app/page.tsx"
Add-FileBlock "apps/web/app/login/page.tsx"
Add-FileBlock "apps/web/app/dashboard/page.tsx"
Add-FileBlock "apps/web/app/analyze/page.tsx"
Add-FileBlock "apps/web/components/WorldMapHero.tsx"
Add-FileBlock "apps/web/components/DecisionCard.tsx"
Add-FileBlock "apps/web/app/api/analyze/route.ts"
Add-FileBlock "apps/web/app/api/orders/route.ts"
Add-FileBlock "apps/web/.env.local.example"

# Admin (apps/admin)
Add-Content  "## apps/admin key files"
Add-FileBlock "apps/admin/app/dashboard/page.tsx"
Add-FileBlock "apps/admin/app/settings/page.tsx"
Add-FileBlock "apps/admin/.env.local.example"

# Analyzer service
Add-Content  "## services/analyzer"
Add-FileBlock "services/analyzer/main.py"
Add-FileBlock "services/analyzer/requirements.txt"
Add-FileBlock "services/analyzer/.env.example"

# Executor service
Add-Content  "## services/executor"
Add-FileBlock "services/executor/main.py"
Add-FileBlock "services/executor/requirements.txt"
Add-FileBlock "services/executor/.env.example"

# Health checks
Add-Content  "## Health Checks
`"
try { Add-Content  ("analyzer /health -> " + (Invoke-WebRequest http://localhost:7001/health -UseBasicParsing).Content) } catch { Add-Content  ("analyzer /health error -> " + .Exception.Message) }
try { Add-Content  ("executor /health -> " + (Invoke-WebRequest http://localhost:7002/health -UseBasicParsing).Content) } catch { Add-Content  ("executor /health error -> " + .Exception.Message) }
Add-Content  "`"

Write-Host "
Generated: "
