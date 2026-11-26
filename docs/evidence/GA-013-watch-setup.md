# GA-013.11: the watcher's secrets and Anthropic limit

Criterion 11 asks for two secrets on moxywolf-plugins and a key in its own Anthropic Console workspace with a monthly limit Dorian sets, recorded in his words.

## Record

- 2026-11-25, `MOXYWOLF_AGENT_APP_KEY`: set by the agent with Dorian's `gh` login, on his instruction ("Do this for me"), from the app's private key in the vault. `gh secret list` shows it.
- 2026-11-25, `GSTACK_WATCH_ANTHROPIC_KEY`: set by Dorian. In his words, 16:14 PT:

  > it says default. No limit. I dded its key as GSTACK_WATCH_ANTHROPIC_KEY.

## Open

The key is in the Console's Default workspace with no spend limit, so the watcher has no cap of its own. Criterion 11's own workspace and monthly limit are not met yet. What bounds a run today is the 40-turn cap per fix and one run at a time.
