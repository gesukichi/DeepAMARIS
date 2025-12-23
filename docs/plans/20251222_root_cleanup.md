---
title: Root Directory Cleanup Plan
created_date: 2025-12-22
author: GitHub Copilot
purpose: Organize the root directory by moving non-essential files to appropriate subdirectories, excluding .zip files.
related_tasks: User request for cleanup during deployment
---

## Objective
Clean up the root directory `c:\Users\you\app-aoai-chatGPT_WebSearchDeploy_kai` to improve readability and organization.

## Strategy
Move files into existing subdirectories based on their type and purpose.

## File Moves

### Documentation (`docs/`)
- `AZURE_DEPLOYMENT_FILE_LOCKING_INVESTIGATION.md` -> `docs/reports/`
- `test_api_demo.md` -> `docs/tests/`
- `test_api_flow.md` -> `docs/tests/`
- `test_frontend_backend.md` -> `docs/tests/`
- `test_system_diagram.md` -> `docs/tests/`

### Deployment Scripts (`deploy_scripts/`)
- `check-deploy-readiness.ps1` -> `deploy_scripts/`
- `deploy-fast.ps1` -> `deploy_scripts/`
- `deploy-private.sh` -> `deploy_scripts/`

### General Scripts (`scripts/`)
- `start-local.cmd` -> `scripts/`
- `uvx.bat` -> `scripts/`
- `test_curl_examples.sh` -> `scripts/`

### Configuration (`config/`)
- `prod-auth-settings.json` -> `config/`
- `staging-auth-body.json` -> `config/`
- `staging-auth-properties.json` -> `config/`

### Archive/Debug (`archive/`)
- `debug_feature_flag.py` -> `archive/debug/`
- `debug_tdd_test.py` -> `archive/debug/`
- `staging-config-backup-20250909-135355.json` -> `archive/config-backups/`
- `network_test_log_20250917_115724.json` -> `archive/logs/` (Create `archive/logs` if not exists, or just `archive/`)

### Test Data (`tests/data/` or `postman/`)
- `test_collection.json` -> `postman/` (Assuming it's a collection, `postman` folder exists)

## Execution Steps
1. Create necessary subdirectories if they don't exist (`docs/reports`, `docs/tests`, `archive/logs`).
2. Move files using `mv` command.
3. Verify root directory is clean.
