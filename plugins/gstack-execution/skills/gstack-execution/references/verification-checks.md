# Verification checks — what "it works" is allowed to mean

Canonical text. The SessionStart hook injects this file verbatim, and the
gstack-execution skill points here rather than restating it, so there is exactly
one home for the rule.

Each check either ran or it didn't, and the report says which. They are not
values, and "I was careful" does not satisfy any of them.

**1. Verify through the user's path, under the user's conditions.** Not the
artifact — the path. A database function tested in a SQL console runs as a
different role than the API uses (Supabase enables `pg_safeupdate` for the
PostgREST role, so a bare `DELETE`/`UPDATE` that passes in the console is
refused through the button). A page section checked by reading source is not
checked; load the deployed URL. A rule corrected in a config table is inert if
the code reads a hardcoded constant. Exercise the real path, or name the part
that is unverified.

**2. Never say "press" without a URL, and not before the control renders.**
Naming a button is not directions. Give the address, and confirm the control
appears in that state first — a control built into an unreachable branch looks
finished in the diff and does not exist to the user.

**3. Read the exit code you actually mean.** `$?` after a pipeline is the LAST
stage's status. A command piped through `sed` — to redact a token, say —
reports `sed`'s success, so a crashed process reads as `rc=0`. Use
`${PIPESTATUS[0]}`, or run the command unpiped and post-process separately.

**4. Count before you characterize.** Never call data noisy, clean, duplicated
or safe without the query behind it — least of all when the characterization is
the argument for overriding the user's judgment. "Mostly junk" that turns out to
be two rows in sixty-eight is a guess wearing a summary's clothes.

**5. Before changing a rule, find its second home.** Config tables mirroring
code constants; a glossary defining the same term twice; `CREATE OR REPLACE
FUNCTION` with a changed signature, which OVERLOADS rather than replaces and
leaves the old definition to win the call. Grep for the value, not just the file
you are in.

**6. Say what you verified and what you didn't, as a format.** Every time — the
sentence is visible when it is missing, which is what makes it work where a
resolution does not. "Typechecked but not exercised through the API" is a
complete and useful report. "Done" is not.

An error caught here costs tokens. An error the user catches costs their
attention, and their trust in everything standing next to it. Run the checks
before speaking, not after being corrected.
