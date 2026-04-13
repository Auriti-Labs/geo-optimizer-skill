# CI/CD Integration

Run GEO audits automatically in your CI/CD pipeline. Catch regressions before they hit production.

## Quick Start (GitHub Actions)

Add this to `.github/workflows/geo-audit.yml`:

```yaml
name: GEO Audit
on: [push]

jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: Auriti-Labs/geo-optimizer-skill@v1
        with:
          url: https://yoursite.com
```

That's it. The action installs Python, installs `geo-optimizer-skill`, runs the audit, and reports the score.

## Inputs

| Input | Required | Default | Description |
|-------|----------|---------|-------------|
| `url` | ✅ | — | URL to audit |
| `min-score` | ❌ | `0` | Preferred minimum score (0-100). Fails if score is below. |
| `threshold` | ❌ | `0` | Deprecated alias for `min-score`. |
| `format` | ❌ | `json` | Output format: `json`, `sarif`, `junit`, `text` |
| `output-file` | ❌ | `geo-report` | Base name for the output file (no extension) |
| `fail-on-warning` | ❌ | `false` | Fail on warnings too |

## Outputs

| Output | Description |
|--------|-------------|
| `score` | GEO citability score (0-100) |
| `band` | Score band: `critical`, `foundation`, `good`, `excellent` |
| `report-path` | Path to the generated report file |

## Examples

### Enforce a minimum score

```yaml
- uses: Auriti-Labs/geo-optimizer-skill@v1
  with:
    url: https://yoursite.com
    min-score: 70
```

The step fails if the score drops below 70.

### SARIF upload (GitHub Security tab)

```yaml
- uses: Auriti-Labs/geo-optimizer-skill@v1
  with:
    url: https://yoursite.com
    format: sarif
```

When `format: sarif`, results automatically appear in the **Security** tab of your repo under Code Scanning alerts.

> **Note:** SARIF upload requires `security-events: write` permission.

### Post results as a PR comment

```yaml
- uses: Auriti-Labs/geo-optimizer-skill@v1
  id: geo
  with:
    url: https://yoursite.com

- uses: actions/github-script@v7
  if: github.event_name == 'pull_request'
  with:
    script: |
      const score = '${{ steps.geo.outputs.score }}';
      const band = '${{ steps.geo.outputs.band }}';
      const emoji = score >= 80 ? '🟢' : score >= 60 ? '🟡' : '🔴';
      await github.rest.issues.createComment({
        owner: context.repo.owner,
        repo: context.repo.repo,
        issue_number: context.issue.number,
        body: `## ${emoji} GEO Audit Results\n\n| Metric | Value |\n|--------|-------|\n| Score | **${score}**/100 |\n| Band | \`${band}\` |\n\n_Powered by [GEO Optimizer](https://github.com/Auriti-Labs/geo-optimizer-skill)_`
      });
```

### JUnit output (for CI dashboards)

```yaml
- uses: Auriti-Labs/geo-optimizer-skill@v1
  with:
    url: https://yoursite.com
    format: junit
    output-file: geo-results

- uses: dorny/test-reporter@v1
  with:
    name: GEO Audit
    path: geo-results.xml
    reporter: java-junit
```

### Scheduled weekly audit

```yaml
name: Weekly GEO Audit
on:
  schedule:
    - cron: "0 6 * * 1"  # Every Monday at 6 AM UTC

jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: Auriti-Labs/geo-optimizer-skill@v1
        id: geo
        with:
          url: https://yoursite.com
          min-score: 60

      - name: Summary
        run: |
          echo "## GEO Score: ${{ steps.geo.outputs.score }}/100" >> "$GITHUB_STEP_SUMMARY"
```

## Platform Support

The action runs on all GitHub-hosted runners:

- ✅ `ubuntu-latest`
- ✅ `macos-latest`
- ✅ `windows-latest`

Python 3.9+ is supported.

---

## GitLab CI

```yaml
geo-audit:
  image: python:3.12-slim
  stage: test
  script:
    - pip install geo-optimizer-skill
    - geo audit --url https://yoursite.com --format json --output geo-report.json
    - |
      SCORE=$(python3 -c "import json; print(json.load(open('geo-report.json'))['score'])")
      echo "GEO Score: ${SCORE}/100"
      if [ "${SCORE}" -lt 60 ]; then
        echo "Score below threshold!"
        exit 1
      fi
  artifacts:
    paths:
      - geo-report.json
    expire_in: 30 days
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
    - if: $CI_COMMIT_BRANCH == "main"
```

## Jenkins

```groovy
pipeline {
    agent any
    stages {
        stage('GEO Audit') {
            steps {
                sh '''
                    pip install geo-optimizer-skill
                    geo audit --url https://yoursite.com --format json --output geo-report.json
                '''
                script {
                    def report = readJSON file: 'geo-report.json'
                    echo "GEO Score: ${report.score}/100 (${report.band})"
                    if (report.score < 60) {
                        error "GEO score ${report.score} is below threshold 60"
                    }
                }
            }
            post {
                always {
                    archiveArtifacts artifacts: 'geo-report.json'
                }
            }
        }
    }
}
```

## Generic CI (any platform)

The core is just two commands:

```bash
pip install geo-optimizer-skill
geo audit --url https://yoursite.com --format json --output report.json
```

Parse the JSON to get `score` (integer 0-100) and `band` (string). Use these to gate deployments or trigger alerts.
