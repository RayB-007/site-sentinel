#!/usr/bin/env python3
"""Audit a static HTML directory without fetching external URLs."""
import argparse
from dataclasses import asdict, dataclass
import fnmatch
from html.parser import HTMLParser
import json
from pathlib import Path
from urllib.parse import unquote, urlsplit

@dataclass
class Issue:
    file: str
    line: int
    code: str
    message: str
    severity: str = 'error'

class Document(HTMLParser):
    def __init__(self, file):
        super().__init__(convert_charrefs=True)
        self.file = file
        self.links, self.ids, self.headings, self.issues = [], set(), [], []
        self.title, self.description, self.in_title = '', '', False

    def issue(self, code, message, severity='error'):
        self.issues.append(Issue(self.file, self.getpos()[0], code, message, severity))

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get('id'):
            if attrs['id'] in self.ids: self.issue('duplicate-id', f'Duplicate ID: {attrs["id"]}')
            self.ids.add(attrs['id'])
        if tag in ('a', 'link', 'img', 'script', 'iframe', 'source'):
            key = 'href' if tag in ('a', 'link') else 'src'
            if attrs.get(key): self.links.append((attrs[key], self.getpos()[0]))
        if tag == 'img' and 'alt' not in attrs:
            self.issue('missing-alt', 'Image needs an alt attribute; use alt="" for decoration')
        if tag == 'title': self.in_title = True
        if tag == 'meta' and attrs.get('name') == 'description': self.description = attrs.get('content', '').strip()
        if tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            level = int(tag[1])
            if self.headings and level > self.headings[-1] + 1:
                self.issue('heading-skip', f'Heading jumps from h{self.headings[-1]} to h{level}', 'warning')
            self.headings.append(level)

    def handle_startendtag(self, tag, attrs): self.handle_starttag(tag, attrs)
    def handle_endtag(self, tag):
        if tag == 'title': self.in_title = False
    def handle_data(self, data):
        if self.in_title: self.title += data

    def finish(self):
        if not self.title.strip(): self.issue('missing-title', 'Document needs a title')
        if not self.description: self.issue('missing-description', 'Missing meta description', 'warning')
        if self.headings.count(1) != 1: self.issue('h1-count', 'Expected exactly one h1', 'warning')


def audit(directory, exclude=()):
    root = Path(directory).resolve()
    if not root.is_dir(): raise ValueError('Root must be an existing directory')
    docs, issues = {}, []
    for path in sorted(root.rglob('*.html')):
        relative = path.relative_to(root).as_posix()
        if any(fnmatch.fnmatch(relative, pattern) for pattern in exclude): continue
        if not path.resolve().is_relative_to(root):
            issues.append(Issue(relative, 1, 'outside-root', 'HTML symlink leaves site root')); continue
        try:
            doc = Document(relative); doc.feed(path.read_text(encoding='utf-8')); doc.finish()
        except (OSError, UnicodeError) as error:
            issues.append(Issue(relative, 1, 'read-error', str(error))); continue
        docs[path.resolve()] = doc; issues.extend(doc.issues)
    for path, doc in docs.items():
        for value, line in doc.links:
            try: parsed = urlsplit(value)
            except ValueError:
                issues.append(Issue(doc.file, line, 'invalid-url', f'Malformed URL: {value}')); continue
            if parsed.scheme or parsed.netloc: continue
            decoded = unquote(parsed.path)
            target = (root / decoded.lstrip('/')) if decoded.startswith('/') else (path.parent / decoded) if decoded else path
            target = target.resolve()
            if not target.is_relative_to(root):
                issues.append(Issue(doc.file, line, 'outside-root', f'Local link leaves site root: {value}')); continue
            if target.is_dir(): target /= 'index.html'
            if not target.is_file():
                issues.append(Issue(doc.file, line, 'missing-target', f'Missing local target: {value}')); continue
            if parsed.fragment and target.suffix.lower() == '.html':
                destination = docs.get(target)
                if destination is None:
                    try:
                        destination = Document(target.relative_to(root).as_posix()); destination.feed(target.read_text(encoding='utf-8'))
                    except (OSError, UnicodeError): continue
                if unquote(parsed.fragment) not in destination.ids:
                    issues.append(Issue(doc.file, line, 'missing-fragment', f'Missing anchor: {value}'))
    if not docs: issues.append(Issue('.', 1, 'no-html', 'No HTML pages found'))
    return {'pages': len(docs), 'errors': sum(i.severity == 'error' for i in issues),
            'warnings': sum(i.severity == 'warning' for i in issues), 'issues': [asdict(i) for i in issues]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--exclude', action='append', default=[], metavar='GLOB')
    parser.add_argument('--json', action='store_true', help='Machine-readable stdout')
    args = parser.parse_args(argv)
    try: result = audit(args.directory, args.exclude)
    except ValueError as error: parser.error(str(error))
    if args.json: print(json.dumps(result, indent=2))
    else:
        for issue in result['issues']:
            print(f'{issue["file"]}:{issue["line"]}: {issue["severity"]} [{issue["code"]}] {issue["message"]}')
        print(f'{result["pages"]} pages · {result["errors"]} errors · {result["warnings"]} warnings')
    return 1 if result['errors'] else 0

if __name__ == '__main__': raise SystemExit(main())
