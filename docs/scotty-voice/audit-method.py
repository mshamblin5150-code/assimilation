"""Reproduce TOS/TAS index coverage and candidate Scott-label counts.
Outputs only metadata JSON. Does not retain or distribute transcripts.
Python 3 standard library; public read-only HTTP requests.
Counts are labels, not certified utterances. Review interpretation separately.
"""
import hashlib, html, json, re, urllib.request
from urllib.parse import urljoin
BASE = 'http://www.chakoteya.net/StarTrek/'
INDEX = urljoin(BASE, 'episodes.htm')
def fetch(url):
    with urllib.request.urlopen(url, timeout=60) as response:
        return response.read()
index = fetch(INDEX).decode('utf8', errors='replace')
links = [(h, ' '.join(html.unescape(re.sub('<[^>]+>', '', t)).split()))
         for h, t in re.findall(r'<a href="([^"]+)">(.*?)</a>', index, re.S)
         if re.fullmatch(r'(?:\d+b?|TAS\d+)\.htm', h)]
rows = []
for filename, title in links:
    url = urljoin(BASE, filename)
    try:
        raw = fetch(url)
        text = raw.decode('utf8', errors='replace')
        text = re.sub(r'<br\s*/?>', '\n', text, flags=re.I)
        text = html.unescape(re.sub('<[^>]+>', '', text))
        labels = re.findall(r'(?:^|\n)\s*SCOTT(?: \[[^\]]+\])?:', text)
        malformed = [line.strip().split()[0] for line in text.splitlines()
                     if re.match(r'^\s*SCOT', line)
                     and not re.match(r'^\s*SCOTT(?: \[[^\]]+\])?:', line)]
        rows.append(dict(title=title, url=url, bytes=len(raw),
                         sha256=hashlib.sha256(raw).hexdigest(),
                         standard_scott_label_blocks=len(labels),
                         malformed_candidate_labels=malformed))
    except Exception as error:
        rows.append(dict(title=title, url=url, error=str(error)))
print(json.dumps(rows, indent=2))
