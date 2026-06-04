# Failure Policy

## General Repair Rule

For each failure:

```text
1. Read the exact error.
2. Identify whether it is code, dependency, environment, data, or network.
3. Try a minimal repair.
4. Re-run the smallest failing check.
5. Repeat for up to 3 focused attempts.
```

If the same blocker remains after 3 attempts, record it in `STATE.md` and continue only if a fallback exists.

## Dependency Failures

If dependency installation fails:

```text
1. Check Python version.
2. Install only the missing package.
3. If a heavy optional package fails, replace with deterministic fallback.
```

Examples:

```text
chromadb fails -> use KeywordRetriever
sentence-transformers fails -> use KeywordRetriever
akshare fails -> use FixtureAshareDataProvider
matplotlib fails -> skip charts and keep Markdown tables
```

## LLM Failures

If the LLM API fails because of missing key, quota, model, or network:

```text
1. Do not stop.
2. Use deterministic extraction rules.
3. Keep LLM client implemented but not required by tests.
4. Record the limitation in REPORT.md.
```

## Data Failures

If live A-share data fails:

```text
1. Use FixtureAshareDataProvider.
2. Keep AKShare adapter implemented.
3. Mark demo output as fixture-data only.
```

## Source Fetching Failures

If public source fetching fails:

```text
1. Use user-upload mode.
2. Use local fixture markdown documents.
3. Keep source policy tests passing.
```

## Git Failures

If remote push fails:

```text
1. Check git remote.
2. Check branch.
3. Check auth.
4. Keep local commits.
5. Record exact push error in STATE.md.
6. Ask user only if credentials or destructive conflict resolution is required.
```

Never run:

```text
git reset --hard
git checkout -- .
git clean -fd
```

unless the user explicitly requests it.

