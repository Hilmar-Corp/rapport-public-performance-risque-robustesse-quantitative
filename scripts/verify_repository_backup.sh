
#!/usr/bin/env bash

backup_directory="${1:-build/repository-backup}"

if [ ! -f "$backup_directory/repository.bundle" ]; then
  echo "Repository bundle missing."
  exit 1
fi

(
  cd "$backup_directory" || exit 1
  shasum -a 256 -c SHA256SUMS
)

checksum_rc=$?

if [ "$checksum_rc" -ne 0 ]; then
  echo "Repository backup checksum verification failed."
  exit "$checksum_rc"
fi

git bundle verify \
  "$backup_directory/repository.bundle"

bundle_rc=$?

if [ "$bundle_rc" -ne 0 ]; then
  echo "Git bundle verification failed."
  exit "$bundle_rc"
fi

restore_directory="$(
  mktemp -d \
    "${TMPDIR:-/tmp}/hilmarcorp-restore.XXXXXX"
)"

git clone \
  "$backup_directory/repository.bundle" \
  "$restore_directory/repository"

clone_rc=$?

if [ "$clone_rc" -ne 0 ]; then
  echo "Repository restore clone failed."
  exit "$clone_rc"
fi

expected_head="$(
  cat "$backup_directory/expected-head.txt"
)"

actual_head="$(
  git -C "$restore_directory/repository" \
    rev-parse HEAD
)"

if [ "$expected_head" != "$actual_head" ]; then
  echo "Restored HEAD differs from expected HEAD."
  exit 1
fi

git -C "$restore_directory/repository" \
  fsck \
  --full

fsck_rc=$?

rm -rf "$restore_directory"

if [ "$fsck_rc" -ne 0 ]; then
  echo "Restored repository integrity check failed."
  exit "$fsck_rc"
fi

echo "Repository backup restoration passed."
