# 2026-11-27 campaign transition

User requested removal of the Maine state campaign and replacement with federal appellate content. Prior main commit 83f43a479856238c014c07984344a08cdc775c80 was preserved on branch archive/maine-law-court before removal. Main now references the unchanged S0001 connection check, not the old S0002 campaign. No new campaign has been configured. Only this exact migration's deletions are exempted from the history audit; future events remain append-only.

Removed from active main: 42 Maine-specific files (planning, records, review, checkpoint, request, receipt). A branch archive is not privacy or permanent deletion from Git history. The old externally hosted snapshot cannot be unpublished by this repository migration. Site draft is read-only; no deployment or browser testing is asserted.
