#!/usr/bin/env bash
# Writes a small, awkward-on-purpose data set plus a SHA-256 manifest into <dir>.
# Used by 50-seed-t2.sh inside the T2 test containers; needs only bash and coreutils.
# Usage: seed-marker-data.sh <dir>     (refuses a non-empty directory)
set -euo pipefail

if [ $# -ne 1 ] || [ -z "$1" ]; then
  echo "usage: seed-marker-data.sh <dir>" >&2
  exit 2
fi
dir=$1
if [ -d "$dir" ] && [ -n "$(ls -A "$dir")" ]; then
  echo "refusing: $dir is not empty" >&2
  exit 1
fi

mkdir -p "$dir/photos" "$dir/archive/2026" "$dir/docs" "$dir/notes and drafts"

# Incompressible binary files of growing size (64 KiB .. 4 MiB) in two directories.
n=1
for size in 65536 131072 262144 524288 1048576 2097152 4194304; do
  for d in photos archive/2026; do
    head -c "$size" /dev/urandom > "$dir/$d/img-$n.bin"
    n=$((n + 1))
  done
done

# Compressible text files, and names with spaces.
for n in 1 2 3 4 5 6 7 8 9 10; do
  seq 1 $((n * 2000)) > "$dir/docs/numbers-$n.txt"
done
printf 'first draft\n' > "$dir/notes and drafts/meeting notes.txt"
printf 'second draft\n' > "$dir/notes and drafts/shopping list (final).txt"

# Manifest last, so it never lists itself. Paths are relative; verify with: sha256sum -c MANIFEST.sha256
manifest=$(cd "$dir" && find . -type f -print0 | LC_ALL=C sort -z | xargs -0 sha256sum)
printf '%s\n' "$manifest" > "$dir/MANIFEST.sha256"
echo "seeded $dir: $(wc -l < "$dir/MANIFEST.sha256") files"
