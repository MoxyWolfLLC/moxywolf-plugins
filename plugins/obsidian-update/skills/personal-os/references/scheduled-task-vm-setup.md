# Scheduled-Task VM Setup — Drive Service Account

The obsidian-update plugin runs in two distinct environments:

1. **Interactive Cowork session** — the MoxyWolf Vault is mounted as a workspace folder. All reads/writes use the regular `Read`/`Write`/`Edit` tools. No setup beyond mounting the vault in Cowork. This document does not apply.
2. **Scheduled-task VM** — Cowork's nightly task runner spins up a fresh VM with no mounts. The vault must be reached through Google Drive's REST API. This is when `scripts/drive_rest.py` is used, and that helper requires a service account.

This document covers the one-time provisioning of the service account so the scheduled task can write to the MoxyWolf Vault (a Shared/Team Drive) without going through any third-party broker.

## What you'll end up with

- A Google Cloud project (new or existing) with the Drive API enabled.
- A service account in that project, with a JSON key.
- The service account email added to the **MoxyWolf Vault Shared Drive** as **Content Manager** (or higher).
- The JSON key saved on every Mac that runs scheduled tasks, at `~/.config/moxywolf/drive-service-account.json` (or anywhere, pointed-to by the `DRIVE_SERVICE_ACCOUNT_JSON` env var).

## Steps

### 1. Create or open a Google Cloud project

Go to <https://console.cloud.google.com/projectselector2/home/dashboard>. Either reuse an existing MoxyWolf project (recommended — keeps everything in one place) or create a new one named `moxywolf-automation`.

### 2. Enable the Drive API

Inside the project, go to **APIs & Services → Library**, search for "Google Drive API", click it, then click **Enable**. This is free and instant.

### 3. Create the service account

Go to **IAM & Admin → Service Accounts → Create Service Account**.

- **Name:** `moxywolf-obsidian-update`
- **ID:** `moxywolf-obsidian-update` (auto-filled)
- **Description:** "Writes to MoxyWolf Vault from scheduled nightly tasks"
- **Project role:** leave blank — the service account doesn't need project-level IAM, only Drive sharing.

Click **Done**. You'll see it in the list.

### 4. Generate a JSON key

Click into the service account → **Keys** tab → **Add Key → Create new key → JSON**. A JSON file downloads automatically. Keep it secret — anyone with this file can read/write the Drive on the service account's behalf.

### 5. Grant the service account access to the Vault Shared Drive

Open Google Drive in a browser, open the **MoxyWolf Shared Files** Shared Drive (or whichever Shared Drive contains the MoxyWolf Vault). Click **Manage members**. Add the service account email — it looks like `moxywolf-obsidian-update@<project-id>.iam.gserviceaccount.com` and you can copy it from the service account detail page.

Permission level: **Content manager** (can edit files; can't change Shared Drive settings). If you want to be able to create new top-level folders from automations, use **Manager**.

### 6. Place the JSON key on the Mac

Default path the helper looks at:

```
~/.config/moxywolf/drive-service-account.json
```

Create the directory and move the key:

```bash
mkdir -p ~/.config/moxywolf
mv ~/Downloads/<project-id>-<random>.json ~/.config/moxywolf/drive-service-account.json
chmod 600 ~/.config/moxywolf/drive-service-account.json
```

If you'd rather keep the key elsewhere (e.g. 1Password's CLI-mounted secrets), set the env var instead:

```bash
echo 'export DRIVE_SERVICE_ACCOUNT_JSON="/path/to/key.json"' >> ~/.zshrc
source ~/.zshrc
```

The env var takes precedence over the default path.

### 7. Sanity-check it works

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/drive_rest.py" search \
    --folder-id "1MjSabHDWYjjnp17DshdO9pnESLyvm6Gs" --name "GOALS"
```

You should get back a JSON object listing the GOALS file (or similar) in the Personal OS folder. If you get a 404, the service account isn't a member of the Shared Drive — re-do step 5. If you get a 401, the JSON key isn't being read — check the file path and `chmod`.

## Python dependencies

The helper uses `PyJWT` and `cryptography` to sign the service-account assertion. Both are standard on modern Pythons but may need an install on the scheduled-task VM the first time:

```bash
pip3 install --break-system-packages PyJWT cryptography
```

If the scheduled-task VM image already has these, no action needed.

## Rotation

Service-account JSON keys don't expire by default but Google recommends rotating them every 90 days. To rotate:

1. Generate a new key (step 4).
2. Replace the file on each Mac (step 6).
3. Delete the old key from the **Keys** tab in the service account.

If a key is ever compromised, delete it immediately — the service account email stays the same, so any new key works as a drop-in once rotated.

## Why a service account and not user OAuth

User OAuth tokens require an interactive browser flow to refresh, which doesn't work in a scheduled-task VM. Service accounts authenticate non-interactively with a long-lived private key. They're the standard pattern for unattended automations against Google APIs.

## Related

- `${CLAUDE_PLUGIN_ROOT}/scripts/drive_rest.py` — the helper script itself, with docstrings on every subcommand.
- `personal-os/SKILL.md` "Team Drive Read/Write Pattern" section — usage examples in the workflow.
