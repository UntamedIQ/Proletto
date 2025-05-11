#!/usr/bin/env bash
BASE="https://22e42364-079d-4ee7-8480-16ca0c045811-00-2tx98zwt5azo.riker.replit.dev"
ROUTES=(
  "/" 
  "/opportunities"
  "/portfolio"
  "/auth/login"
  "/auth/register"
  "/auth/logout"
  "/get-started"
  "/sign-up"
  "/sign-in"
  "/upgrade"
  "/start-trial"
  "/login.html"
  "/signup.html"
)

echo "🔍 Running live smoke test against $BASE"
for route in "${ROUTES[@]}"; do
  URL="$BASE$route"
  # -L to follow redirects, -o /dev/null to discard body, -s for silent, -w to print status
  STATUS=$(curl -Ls -o /dev/null -w "%{http_code}" "$URL")
  if [[ $STATUS -ge 200 && $STATUS -lt 400 ]]; then
    MARK="✅"
  else
    MARK="❌"
  fi
  printf "%-18s -> %s %s\n" "$route" "$STATUS" "$MARK"
done