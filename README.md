# Site Sentinel

A dependency-free static-site auditor for local HTML directories. It catches broken internal links, missing assets and anchors, duplicate IDs, and images without alt attributes. It also reports basic metadata and heading warnings.

Designed for practical checks before deploying a static site. See the scope section for the checks that require a browser.

## Run

Python 3.10 or newer; no installation required.

```sh
python3 sentinel.py examples/good
python3 sentinel.py /path/to/site --json
python3 sentinel.py /path/to/site --exclude 'vendor/*' --exclude 'apps/fairway/*'
```

The process exits with status 1 for errors and 0 when only warnings or no issues remain. JSON output includes page counts and each issue’s filename, line number, severity, code, and explanation.

## Checks

| Error | What is checked |
|---|---|
| `missing-target` | Local links and image/script/stylesheet/iframe sources exist |
| `missing-fragment` | Linked HTML anchors exist, including on other pages |
| `duplicate-id` | IDs are unique within a document |
| `missing-alt` | Images include an alt attribute; empty alt is valid for decoration |
| `outside-root` | Local paths do not leave the requested site directory |
| `missing-title` | A document has a nonempty title |

Missing meta descriptions, unexpected h1 counts, and skipped heading levels are warnings. URL query strings are ignored for file resolution, and percent-encoded paths and anchors are decoded. Directory URLs map to `index.html`.

## Test

```sh
python3 -m unittest discover -s tests -v
```

Fixtures cover cross-page fragments, encoded filenames, missing assets, decorative images, duplicate IDs, exclusions, path traversal, and empty sites.

## Scope

This tool parses HTML, not a rendered browser DOM. It does not execute JavaScript, evaluate CSS, fetch external URLs, check HTTP status codes, or follow links inside CSS/modules. It assumes a static site with directory-based routes. Pair it with a real browser and deployment checks.

## Portfolio

More projects and background: [rayansh.dev](https://rayansh.dev/).
