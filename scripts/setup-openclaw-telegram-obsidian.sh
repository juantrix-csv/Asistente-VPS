#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  setup-openclaw-telegram-obsidian.sh --telegram-bot-token TOKEN --obsidian-vault-path PATH [options]

Options:
  --allow-from ID[,ID]       Telegram numeric user ID allowlist. Without it, DM pairing is used.
  --install-openclaw         Install openclaw@latest with npm when missing.
  --start-gateway            Start `openclaw gateway` after setup.
  --use-obsidian-cli         Enable official Obsidian CLI integration.
  -h, --help                 Show this help.
EOF
}

telegram_bot_token=""
obsidian_vault_path=""
allow_from_csv=""
install_openclaw=false
start_gateway=false
use_obsidian_cli=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --telegram-bot-token)
      telegram_bot_token="${2:-}"
      shift 2
      ;;
    --obsidian-vault-path)
      obsidian_vault_path="${2:-}"
      shift 2
      ;;
    --allow-from)
      allow_from_csv="${2:-}"
      shift 2
      ;;
    --install-openclaw)
      install_openclaw=true
      shift
      ;;
    --start-gateway)
      start_gateway=true
      shift
      ;;
    --use-obsidian-cli)
      use_obsidian_cli=true
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ -z "$telegram_bot_token" || -z "$obsidian_vault_path" ]]; then
  usage >&2
  exit 1
fi

if ! command -v node >/dev/null 2>&1; then
  echo "Node.js is required. Install Node 24 or Node 22.14+." >&2
  exit 1
fi

node_major="$(node --version | sed 's/^v//' | cut -d. -f1)"
if [[ "$node_major" -lt 22 ]]; then
  echo "OpenClaw requires Node 22.14+; detected $(node --version)." >&2
  exit 1
fi

if ! command -v openclaw >/dev/null 2>&1; then
  if [[ "$install_openclaw" == true ]]; then
    npm install -g openclaw@latest
  else
    echo "openclaw is not installed. Re-run with --install-openclaw or run: npm install -g openclaw@latest" >&2
    exit 1
  fi
fi

vault_path="$(node -e 'console.log(require("path").resolve(process.argv[1]))' "$obsidian_vault_path")"
mkdir -p "$vault_path"

openclaw_home="${OPENCLAW_HOME:-$HOME/.openclaw}"
workspace_path="$openclaw_home/workspace"
skills_path="$workspace_path/skills"
config_path="$openclaw_home/openclaw.json"

mkdir -p "$skills_path"

if [[ -f "$config_path" ]]; then
  backup_path="$config_path.bak-$(date +%Y%m%d-%H%M%S)"
  cp "$config_path" "$backup_path"
  echo "Backup created: $backup_path"
fi

dm_policy="pairing"
if [[ -n "$allow_from_csv" ]]; then
  dm_policy="allowlist"
fi

export TELEGRAM_BOT_TOKEN_FOR_NODE="$telegram_bot_token"
export OBSIDIAN_VAULT_PATH_FOR_NODE="$vault_path"
export ALLOW_FROM_CSV_FOR_NODE="$allow_from_csv"
export DM_POLICY_FOR_NODE="$dm_policy"
export USE_OBSIDIAN_CLI_FOR_NODE="$use_obsidian_cli"
gateway_token="$(node -e 'process.stdout.write(require("crypto").randomBytes(32).toString("hex"))')"
export GATEWAY_TOKEN_FOR_NODE="$gateway_token"

node > "$config_path" <<'NODE'
const allowFrom = process.env.ALLOW_FROM_CSV_FOR_NODE
  ? process.env.ALLOW_FROM_CSV_FOR_NODE.split(",").map((item) => item.trim()).filter(Boolean)
  : [];

const vaultPath = process.env.OBSIDIAN_VAULT_PATH_FOR_NODE;
const vaultName = require("path").basename(vaultPath) || "Clawd";

const config = {
  gateway: {
    mode: "local",
    bind: "loopback",
    auth: {
      mode: "token",
      token: process.env.GATEWAY_TOKEN_FOR_NODE,
    },
  },
  channels: {
    telegram: {
      enabled: true,
      botToken: process.env.TELEGRAM_BOT_TOKEN_FOR_NODE,
      dmPolicy: process.env.DM_POLICY_FOR_NODE,
      allowFrom,
      groups: {
        "*": {
          requireMention: true,
        },
      },
      streaming: "partial",
      linkPreview: false,
      textChunkLimit: 3500,
    },
  },
  plugins: {
    entries: {
      "memory-wiki": {
        enabled: true,
        config: {
          vaultMode: "isolated",
          vault: {
            path: vaultPath,
            renderMode: "obsidian",
          },
          obsidian: {
            enabled: true,
            vaultName,
            useOfficialCli: process.env.USE_OBSIDIAN_CLI_FOR_NODE === "true",
            openAfterWrites: false,
          },
          ingest: {
            autoCompile: true,
            maxConcurrentJobs: 1,
            allowUrlIngest: true,
          },
          search: {
            backend: "local",
            corpus: "wiki",
          },
          context: {
            includeCompiledDigestPrompt: false,
          },
          render: {
            preserveHumanBlocks: true,
            createBacklinks: true,
            createDashboards: true,
          },
        },
      },
    },
  },
};

process.stdout.write(`${JSON.stringify(config, null, 2)}\n`);
NODE

chmod 600 "$config_path"
chmod 700 "$openclaw_home"
echo "Config written: $config_path"

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
local_skill_path="$repo_root/skills/obsidian-vault"
target_skill_path="$skills_path/obsidian-vault"

if [[ -d "$local_skill_path" ]]; then
  rm -rf "$target_skill_path"
  cp -R "$local_skill_path" "$target_skill_path"
  echo "Skill copied: $target_skill_path"
fi

echo
echo "Ready."
echo "Obsidian vault: $vault_path"
echo "Telegram DM policy: $dm_policy"

if [[ -z "$allow_from_csv" ]]; then
  cat <<'EOF'
Now DM your bot and approve pairing with:
  openclaw pairing list telegram
  openclaw pairing approve telegram <CODE>
EOF
fi

echo
echo "Checking config..."
openclaw doctor

if [[ "$start_gateway" == true ]]; then
  echo
  echo "Starting gateway..."
  openclaw gateway
fi
