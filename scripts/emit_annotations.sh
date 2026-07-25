#!/bin/bash
# Emit GitHub Actions annotations from pytest log files
for log in /tmp/pg-test-*.log; do
  [ -f "$log" ] || continue
  while IFS= read -r line; do
    case "$line" in
      *FAILED*) echo "::error title=FAILED TEST::$line" ;;
      *ERROR*) echo "::error title=TEST ERROR::$line" ;;
      *"E "*) echo "::error title=ASSERT FAIL::$line" ;;
      *assert*) echo "::error title=ASSERTION::$line" ;;
    esac
  done < "$log"
done
