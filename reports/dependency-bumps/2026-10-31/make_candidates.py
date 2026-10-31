"""Build candidate A (12 clean bumps) and candidate B (A + the OpenTelemetry family in lockstep)."""
import json, re
from pathlib import Path

HERE = Path(__file__).parent
norm = lambda n: re.sub(r"[-_.]+", "-", n).lower()
raw = (HERE / "requirements.baseline.txt").read_text(encoding="utf-8", newline="")
nl = "\r\n" if "\r\n" in raw else "\n"
base = raw.replace("\r\n", "\n").split("\n")
targets = json.loads((HERE / "targets.json").read_text(encoding="utf-8"))
otel = json.loads((HERE / "otel-resolved.json").read_text(encoding="utf-8"))
otel = {norm(k): v for k, v in otel.items()}


def bump(lines, mapping):
    out, done = [], set()
    for line in lines:
        m = re.match(r"^([A-Za-z0-9_.\-]+)==(\S+)(\s*#.*)?\s*$", line)
        if m and norm(m.group(1)) in mapping:
            key = norm(m.group(1))
            out.append(f"{m.group(1)}=={mapping[key]}{m.group(3) or ''}")
            done.add(key)
        else:
            out.append(line)
    return out, done


# A: every vulnerable package except opentelemetry-api (its fix needs the whole family)
a_map = {k: v["target"] for k, v in targets.items() if v["target"] and k != "opentelemetry-api"}
a_lines, a_done = bump(base, a_map)
assert a_done == set(a_map), set(a_map) - a_done

# B: A plus the whole OpenTelemetry family at the versions pip resolved together
b_lines, b_done = bump(a_lines, otel)
existing = {norm(re.split(r"[=<>~!\[; ]", l.strip())[0]) for l in b_lines if l.strip() and not l.startswith("#")}
new_pins = sorted(k for k in otel if k not in existing)
for k in new_pins:  # keep the file's alphabetical order: insert before the first line that sorts after it
    idx = next((i for i, l in enumerate(b_lines) if l.strip() and not l.startswith("#") and norm(re.split(r"[=<>~!\[; ]", l.strip())[0]) > k), len(b_lines))
    b_lines.insert(idx, f"{k}=={otel[k]}")
(HERE / "requirements.candidateA.txt").write_text(nl.join(a_lines), encoding="utf-8", newline="")
(HERE / "requirements.candidateB.txt").write_text(nl.join(b_lines), encoding="utf-8", newline="")
print(f"A: {len(a_done)} packages bumped.")
print(f"B: A plus {len(b_done)} OpenTelemetry pins updated and {len(new_pins)} NEW pins added: {new_pins}")
