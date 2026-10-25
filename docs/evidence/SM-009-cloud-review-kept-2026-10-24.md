# SM-009 criterion 2: a cloud review copied to the vault and read back

Captured on 2026-10-24 from the device shell linked to Dorian's Mac, with this branch's `session_record.py`, against the review the MW Plugins cloud session published at session end. That publish ran before `--standing-consent` existed, so its receipt records no consent field and reads as per-session; the standing path is covered in-repo by `StandingConsent` in `plugins/project-init/tests/test_session_record.py`.

Vault copy: `MoxyWolf Vault/Projects/Moxywolf Plugins/11-Knowledge/session-records/6e614c6d-0a4d-55d1-ae61-e7cc68f5aecc-20261024-165628-fdf665/`

`session_record.py read <that folder>`, first five lines:

```
session 6e614c6d-0a4d-55d1-ae61-e7cc68f5aecc
publication 20261024-165628-fdf665
audience MoxyWolf team
confirmed by dorianatmoxywolf at 2026-10-24T23:56:33Z (per-session consent)
verified: every file matches hashes.sha256 and the receipt
```

`session_record.py list <session-records folder>`:

```
verified  6e614c6d-0a4d-55d1-ae61-e7cc68f5aecc-20261024-165628-fdf665  publication 20261024-165628-fdf665  session 6e614c6d-0a4d-55d1-ae61-e7cc68f5aecc  confirmed by dorianatmoxywolf  (per-session consent)
examined 1 folder(s): 1 verified, 0 refused
```
