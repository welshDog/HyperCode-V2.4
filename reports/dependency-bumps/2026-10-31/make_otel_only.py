"""Apply ONLY the OpenTelemetry family bump (resolved together by pip) to a requirements file.
Usage: python make_otel_only.py <input requirements.txt> <output requirements.txt>"""
import json, re, sys
from pathlib import Path
norm = lambda n: re.sub(r"[-_.]+", "-", n).lower()
otel = {norm(k): v for k, v in json.loads((Path(__file__).parent / "otel-resolved.json").read_text(encoding="utf-8")).items()}
raw = Path(sys.argv[1]).read_text(encoding="utf-8", newline="")
nl = "\r\n" if "\r\n" in raw else "\n"
lines, done = [], set()
for line in raw.replace("\r\n", "\n").split("\n"):
    m = re.match(r"^([A-Za-z0-9_.\-]+)==(\S+)(\s*#.*)?\s*$", line)
    if m and norm(m.group(1)) in otel:
        lines.append(f"{m.group(1)}=={otel[norm(m.group(1))]}{m.group(3) or ''}"); done.add(norm(m.group(1)))
    else:
        lines.append(line)
present = {norm(re.split(r"[=<>~!\[; ]", l.strip())[0]) for l in lines if l.strip() and not l.startswith("#")}
new = sorted(k for k in otel if k not in present)
for k in new:
    i = next((i for i, l in enumerate(lines) if l.strip() and not l.startswith("#") and norm(re.split(r"[=<>~!\[; ]", l.strip())[0]) > k), len(lines))
    lines.insert(i, f"{k}=={otel[k]}")
Path(sys.argv[2]).write_text(nl.join(lines), encoding="utf-8", newline="")
print(f"updated {len(done)} OpenTelemetry pins, added {len(new)} new: {new}")
