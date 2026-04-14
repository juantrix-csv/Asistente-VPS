[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)]
  [string]$TelegramBotToken,

  [Parameter(Mandatory = $true)]
  [string]$ObsidianVaultPath,

  [string[]]$AllowFrom = @(),

  [switch]$InstallOpenClaw,

  [switch]$StartGateway,

  [switch]$UseObsidianCli
)

$ErrorActionPreference = "Stop"

function Resolve-FullPath {
  param([Parameter(Mandatory = $true)][string]$Path)

  $expanded = [Environment]::ExpandEnvironmentVariables($Path)
  if ([System.IO.Path]::IsPathRooted($expanded)) {
    return [System.IO.Path]::GetFullPath($expanded)
  }

  return [System.IO.Path]::GetFullPath((Join-Path (Get-Location) $expanded))
}

function New-BackupIfExists {
  param([Parameter(Mandatory = $true)][string]$Path)

  if (Test-Path -LiteralPath $Path) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $backupPath = "$Path.bak-$stamp"
    Copy-Item -LiteralPath $Path -Destination $backupPath -Force
    Write-Host "Backup creado: $backupPath"
  }
}

if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
  throw "Node.js no esta en PATH. Instala Node 24 o usa el instalador oficial de OpenClaw."
}

$nodeVersionRaw = (& node --version).TrimStart("v")
$nodeMajor = [int]($nodeVersionRaw.Split(".")[0])
if ($nodeMajor -lt 22) {
  throw "OpenClaw requiere Node 22.14+; detectado: v$nodeVersionRaw"
}

if (-not (Get-Command openclaw -ErrorAction SilentlyContinue)) {
  if ($InstallOpenClaw) {
    Write-Host "Instalando openclaw@latest..."
    npm install -g openclaw@latest
  } else {
    throw "openclaw no esta instalado. Ejecuta de nuevo con -InstallOpenClaw o instala: npm install -g openclaw@latest"
  }
}

$vaultPath = Resolve-FullPath $ObsidianVaultPath
New-Item -ItemType Directory -Force -Path $vaultPath | Out-Null

$openClawHome = Join-Path $HOME ".openclaw"
$workspacePath = Join-Path $openClawHome "workspace"
$skillsPath = Join-Path $workspacePath "skills"
$configPath = Join-Path $openClawHome "openclaw.json"

New-Item -ItemType Directory -Force -Path $openClawHome | Out-Null
New-Item -ItemType Directory -Force -Path $skillsPath | Out-Null

[Environment]::SetEnvironmentVariable("TELEGRAM_BOT_TOKEN", $TelegramBotToken, "User")
$env:TELEGRAM_BOT_TOKEN = $TelegramBotToken

$dmPolicy = "pairing"
if ($AllowFrom.Count -gt 0) {
  $dmPolicy = "allowlist"
}

$gatewayToken = (& node -e "process.stdout.write(require('crypto').randomBytes(32).toString('hex'))")

$config = [ordered]@{
  gateway = [ordered]@{
    mode = "local"
    bind = "loopback"
    auth = [ordered]@{
      mode = "token"
      token = $gatewayToken
    }
  }
  channels = [ordered]@{
    telegram = [ordered]@{
      enabled = $true
      dmPolicy = $dmPolicy
      allowFrom = $AllowFrom
      groups = [ordered]@{
        "*" = [ordered]@{
          requireMention = $true
        }
      }
      streaming = "partial"
      linkPreview = $false
      textChunkLimit = 3500
    }
  }
  plugins = [ordered]@{
    entries = [ordered]@{
      "memory-wiki" = [ordered]@{
        enabled = $true
        config = [ordered]@{
          vaultMode = "isolated"
          vault = [ordered]@{
            path = $vaultPath
            renderMode = "obsidian"
          }
          obsidian = [ordered]@{
            enabled = $true
            vaultName = (Split-Path -Path $vaultPath -Leaf)
            useOfficialCli = [bool]$UseObsidianCli
            openAfterWrites = $false
          }
          ingest = [ordered]@{
            autoCompile = $true
            maxConcurrentJobs = 1
            allowUrlIngest = $true
          }
          search = [ordered]@{
            backend = "local"
            corpus = "wiki"
          }
          context = [ordered]@{
            includeCompiledDigestPrompt = $false
          }
          render = [ordered]@{
            preserveHumanBlocks = $true
            createBacklinks = $true
            createDashboards = $true
          }
        }
      }
    }
  }
}

New-BackupIfExists $configPath
$config | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $configPath -Encoding UTF8
Write-Host "Config escrita: $configPath"

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$localSkillPath = Join-Path $repoRoot "skills\obsidian-vault"
$targetSkillPath = Join-Path $skillsPath "obsidian-vault"

if (Test-Path -LiteralPath $localSkillPath) {
  if (Test-Path -LiteralPath $targetSkillPath) {
    Remove-Item -LiteralPath $targetSkillPath -Recurse -Force
  }
  Copy-Item -LiteralPath $localSkillPath -Destination $targetSkillPath -Recurse
  Write-Host "Skill copiada: $targetSkillPath"
}

Write-Host ""
Write-Host "Listo."
Write-Host "Vault Obsidian: $vaultPath"
Write-Host "Politica DM Telegram: $dmPolicy"
if ($AllowFrom.Count -eq 0) {
  Write-Host "Ahora mandale un DM al bot y aproba el pairing con:"
  Write-Host "  openclaw pairing list telegram"
  Write-Host "  openclaw pairing approve telegram <CODIGO>"
}

Write-Host ""
Write-Host "Chequeando config..."
openclaw doctor

if ($StartGateway) {
  Write-Host ""
  Write-Host "Arrancando gateway..."
  openclaw gateway
}
