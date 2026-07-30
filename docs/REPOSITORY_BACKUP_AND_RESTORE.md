
# Repository Backup, Restoration and Incident Procedure

## Scope

This procedure covers Git history, tags, controlled release artifacts,
workflows and repository configuration evidence.

## Backup

A complete Git bundle is generated with:

~~~text
scripts/backup_repository.sh build/repository-backup
~~~

The bundle includes the expected HEAD commit, the origin URL and SHA-256
checksums.

## Restoration test

The backup is restored and verified with:

~~~text
scripts/verify_repository_backup.sh build/repository-backup
~~~

The control verifies the bundle, performs a clean clone, compares the restored
HEAD and executes `git fsck --full`.

## Frequency

The restoration test runs on relevant pull requests, on `main`, monthly and
on manual request.

## Incident response

If repository integrity is questioned:

1. suspend release publication;
2. preserve the repository and workflow logs;
3. compare protected refs and release assets against their hashes;
4. restore the latest verified bundle in an isolated directory;
5. document the root cause and corrective action;
6. resume publication only after all controls pass.
