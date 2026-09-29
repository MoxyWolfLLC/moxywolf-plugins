# XE-014 criterion 9: `aigateway.env` ends in a newline

Read 2026-09-29T21:27:58Z from `MoxyWolf Vault/_Shared Knowledge/Agents and Plugins/aigateway.env`. The key itself isn't recorded here.

| | Before (2026-09-22 measurement) | Now |
|---|---|---|
| Bytes | 79 | 80 |
| Final byte | the key's last character | `0a` (newline) |
| Lines (`wc -l`) | 0 | 1 |
| Line shape | `AI_GATEWAY_API_KEY=` + 60 characters | `AI_GATEWAY_API_KEY=` + 60 characters |

The loader doesn't depend on this: `test_packet_coverage_run.py::test_a_key_on_a_last_line_with_no_newline_is_read` covers the old shape.
