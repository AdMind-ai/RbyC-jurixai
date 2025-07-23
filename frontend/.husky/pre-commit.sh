#!/bin/sh
echo '🔍 Checking for linting errors and running tests before committing...'

echo '🧪 Running tests...'
npx vitest related --changed || exit 1

echo '🖌 Formatting code...'
npm run format

echo '🚨 Running ESLint...'
npm run lint || exit 1

echo '✅ All checks passed. Ready to commit!'
