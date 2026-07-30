
#!/usr/bin/env bash

destination="${1:-build/repository-backup}"

mkdir -p "$destination"
mkdir_rc=$?

if [ "$mkdir_rc" -ne 0 ]; then
  echo "Unable to create backup destination."
  exit "$mkdir_rc"
fi

git bundle create \
  "$destination/repository.bundle" \
  --all

bundle_rc=$?

if [ "$bundle_rc" -ne 0 ]; then
  echo "Unable to create repository bundle."
  exit "$bundle_rc"
fi

git rev-parse HEAD \
  > "$destination/expected-head.txt"

head_rc=$?

git config --get remote.origin.url \
  > "$destination/origin-url.txt"

origin_rc=$?

(
  cd "$destination" || exit 1

  shasum -a 256 \
    repository.bundle \
    expected-head.txt \
    origin-url.txt \
    > SHA256SUMS
)

hash_rc=$?

if [ "$head_rc" -ne 0 ] || \
   [ "$origin_rc" -ne 0 ] || \
   [ "$hash_rc" -ne 0 ]; then

  echo "Repository backup metadata failed."
  exit 1
fi

echo "Repository backup created: $destination"
