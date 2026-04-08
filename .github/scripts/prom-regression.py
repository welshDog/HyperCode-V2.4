import json
import os
import sys
import urllib.parse
import urllib.request

def query(prom_url: str, q: str) -> float:
    url = f"{prom_url}/api/v1/query?{urllib.parse.urlencode({'query': q})}"
    with urllib.request.urlopen(url) as r:
        data = json.loads(r.read())
    if data.get('status') != 'success':
        raise RuntimeError('prom query failed')
    res = data['data']['result']
    if not res:
        return float('nan')
    v = float(res[0]['value'][1])
    return v

def fmt_target(t: str) -> str:
    return t.replace('http://', '').replace('https://', '')

def main():
    prom = os.getenv('PROM_URL', 'http://localhost:9090')
    with open(os.getenv('PROM_BASELINE', '.github/prom-baseline.json'), 'r') as f:
        baseline = json.load(f)
    failures = []
    for target, bl in baseline.items():
        inst = fmt_target(target)
        q_base = f'probe_duration_seconds{{instance="{inst}"}}'
        p50 = query(prom, f'quantile_over_time(0.5, {q_base}[5m])')
        p95 = query(prom, f'quantile_over_time(0.95, {q_base}[5m])')
        p99 = query(prom, f'quantile_over_time(0.99, {q_base}[5m])')
        def reg(curr, base):
            if base == 0 or curr != curr:
                return 0.0
            return (curr - base) / base * 100.0
        r50 = reg(p50, bl['p50'])
        r95 = reg(p95, bl['p95'])
        r99 = reg(p99, bl['p99'])
        if any(x > 5.0 for x in (r50, r95, r99)):
            failures.append({
                'target': target,
                'curr': {'p50': p50, 'p95': p95, 'p99': p99},
                'baseline': bl,
                'regression_pct': {'p50': r50, 'p95': r95, 'p99': r99},
            })
    if failures:
        print(json.dumps({'status': 'fail', 'failures': failures}, indent=2))
        sys.exit(1)
    else:
        print(json.dumps({'status': 'ok'}, indent=2))

if __name__ == '__main__':
    main()
