# vault-review-list
1. Add the list command
   - `session_record.py list <folder>` examines every folder directly inside it and prints one line per folder: `verified` or `refused`, the folder's name, and for a verified one the publication id, the session and who confirmed it, using the same checks as `read`
   - it ends with a line saying how many folders it examined and how many verified; a folder with nothing in it says so and exits 2
   - it exits 0 when every folder verified and 1 when any was refused, and it writes nothing
2. Name list in /session-review
   - the cloud-session paragraph of `/session-review` says to run `list` on the vault's `11-Knowledge/session-records/` folder to find the reviews kept there
