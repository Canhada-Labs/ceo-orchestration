#!/usr/bin/env bash
# Does an upgrade REGRESS the root pointer from a substituted path back to an
# unsubstituted placeholder?
set -u
REPO="$1"
D="$( mktemp -d )"
P="$D/PROTOCOL.md"

"$REPO/scripts/install.sh" "$D" --ceremony maintainer >/dev/null 2>&1
echo "after INSTALL:"
grep -c 'PROTOCOL_SOURCE' "$P" 2>/dev/null | xargs echo "  literal {{PROTOCOL_SOURCE}} occurrences:"
sed -n '3,4p' "$P" | sed 's/^/  | /'

"$REPO/scripts/upgrade.sh" "$D" >/dev/null 2>&1
echo "after UPGRADE:"
grep -c 'PROTOCOL_SOURCE' "$P" 2>/dev/null | xargs echo "  literal {{PROTOCOL_SOURCE}} occurrences:"
sed -n '3,4p' "$P" | sed 's/^/  | /'

echo "-----"
if [ "$( grep -c 'PROTOCOL_SOURCE' "$P" 2>/dev/null )" -gt 0 ]; then
  echo "VERDICT: the upgrade left an UNSUBSTITUTED placeholder in the pointer"
else
  echo "VERDICT: pointer stays substituted"
fi
rm -rf "$D"
