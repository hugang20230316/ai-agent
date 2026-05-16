# Publish Dev Execution Rules

This file contains shared release rules. Use the machine's Python 3 executable; examples use `python3 scripts/publish_dev.py`.

## Shared Modes

| Request | Writes |
| --- | --- |
| publish / release | Yes |
| preview / check only | No |
| publish selected component | Yes |
| update configured apps to a known tag | Optional, depending on preview/what-if mode |

## Shared Rules

- Read repository, Git provider, Argo CD, app list, component map, tag pattern, timeout values, credentials, and local state from local configuration.
- Reuse in-flight publish state instead of creating duplicate tags or duplicate app syncs.
- Preview mode must not create tags or sync apps.
- Real publish must report planned tag, final release tag, app updates, unchanged apps, and failures.
- Timeout results require one read-only Git provider or Argo CD status refresh before reporting final failure.
- Credentials and local state must stay outside Git.
