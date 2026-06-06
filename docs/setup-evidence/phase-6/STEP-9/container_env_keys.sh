#!/bin/sh
for item in $(env); do
  key=${item%%=*}
  case "$key" in
    *REDIS*|*PASSWORD*) echo "$key=<redacted>" ;;
  esac
done
