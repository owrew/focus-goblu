# Commit history and verification

The first three commits are reconstructed from the saved 0.1, 0.2 and 0.3 source archives. They use the current import time and the configured local Git identity. Subsequent commits capture desktop support, the browser companion, and repository documentation as distinct changes. This history documents the available milestones without creating placeholder commits to meet a count.

Run `py -3.11 scripts/import-history.py "<outputs directory>"` once from an uninitialized project directory. The script imports the three saved archives and stages an explicit list of current source paths. It runs `git fsck` and shows the commit history. GitHub authentication and push happen separately. Cryptographic commit verification depends on the configured signing key.
