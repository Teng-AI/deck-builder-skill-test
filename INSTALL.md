# Installing deck-builder

Works on **Claude Code** and **Codex**, CLI or desktop app. Everything the
skill needs is in this folder; the scripts run on plain `python3` (standard
library only).

## The one-sentence install

Paste the sentence for your tool into a chat with it, with the repo URL you
were given:

**Claude Code**

> Clone REPO_URL and copy its contents into `~/.claude/skills/deck-builder/`,
> then read that SKILL.md and confirm the deck-builder skill is ready.

**Codex**

> Clone REPO_URL and copy its contents into `~/.codex/skills/deck-builder/`,
> then read that SKILL.md and confirm the deck-builder skill is ready.

Your agent does the rest. Start a fresh session afterwards so the skill list
reloads.

## Installing by hand

```bash
git clone REPO_URL deck-builder-skill
mkdir -p ~/.claude/skills
cp -R deck-builder-skill ~/.claude/skills/deck-builder
```

For Codex use `~/.codex/skills/deck-builder` instead. **Codex note:** if
`~/.codex/skills` exists at all, Codex reads only it and silently ignores
`~/.agents/skills`, so put the skill where the rest of yours already live.

Project-scoped installs work too: `.claude/skills/deck-builder/` inside any
repo makes the skill available to that project only.

## Check it works

Ask your agent to "build a deck from the worked example" or run the example
directly:

```bash
python3 ~/.claude/skills/deck-builder/scripts/check_deck.py \
  ~/.claude/skills/deck-builder/examples/quarterly.deck.json
```

A summary line ending in `0 failed` means the install is good.

## Uninstall

Delete the `deck-builder` folder from your skills directory. Nothing else is
touched.
