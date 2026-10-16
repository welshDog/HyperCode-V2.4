# probe_inter_agent_key.ps1 - READ-ONLY: does every holder of the shared inter-agent key get accepted by every peer?
#
# For each holder it runs a tiny python snippet INSIDE the container (base64, so Windows PowerShell 5.1 cannot mangle
# quoting), which sends that container's own key (HYPERCODE_API_KEY_FILE > HYPERCODE_API_KEY > API_KEY_FILE > API_KEY) as
# X-API-Key to GET /__authprobe on every peer. 404 = accepted (route does not exist but auth passed), 401/403 = rejected,
# "down" = no answer. A trailing "?" (e.g. 404?) means the peer ALSO answered 404 to a deliberately wrong key, so it
# does not enforce the key on this path and the result proves nothing for it. Keys are never printed. See docs/AGENT_SECRET_FILES.md ("The shared inter-agent key").
# Usage: powershell -NoProfile -ExecutionPolicy Bypass -File scripts\probe_inter_agent_key.ps1
$ErrorActionPreference = 'Continue'

# container -> port its HTTP server listens on
$peers = [ordered]@{
    'crew-orchestrator' = 8080
    'coder-agent'       = 8002
    'qa-engineer'       = 8005
    'safety-shepherd'   = 8096
    'coder-studio'      = 8087
    'evolve-relay'      = 8097
    'governor'          = 8080
}

$py = @'
import os, sys, urllib.request, urllib.error

def key():
    for fvar, var in (("HYPERCODE_API_KEY_FILE", "HYPERCODE_API_KEY"), ("API_KEY_FILE", "API_KEY")):
        f = os.environ.get(fvar)
        if f:
            try:
                return open(f, encoding="utf-8-sig").read().strip()
            except OSError:
                pass
        v = os.environ.get(var)
        if v:
            return v.strip()
    return ""

k = key()


def status(name, port, hdr):
    req = urllib.request.Request("http://%s:%s/__authprobe" % (name, port), headers={"X-API-Key": hdr})
    try:
        return urllib.request.urlopen(req, timeout=4).status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return "down"


out = []
for spec in sys.argv[1:]:
    name, port = spec.split(":")
    code = status(name, port, k)
    # negative control: a wrong key must be refused, otherwise this path proves nothing about that peer
    if code not in (401, 403, "down") and status(name, port, "definitely-wrong-key") not in (401, 403):
        code = "%s?" % code
    out.append("%s=%s" % (name, code))
print("keylen=%d %s" % (len(k), " ".join(out)))
'@
$b64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($py))

$rows = foreach ($from in $peers.Keys) {
    $targets = @($peers.Keys | Where-Object { $_ -ne $from } | ForEach-Object { "${_}:$($peers[$_])" })
    $line = docker exec $from sh -c "echo $b64 | base64 -d > /tmp/_probe.py && python /tmp/_probe.py $($targets -join ' '); rm -f /tmp/_probe.py" 2>&1
    [pscustomobject]@{ From = $from; Result = ("$line").Trim() }
}
foreach ($r in $rows) { "{0,-18} {1}" -f $r.From, $r.Result }

$bad = @($rows | Where-Object { $_.Result -notmatch '^keylen=\d+' -or $_.Result -match '=(401|403|down)' })
$unverified = @($rows | Where-Object { $_.Result -match '=\d+\?' })
if ($bad.Count -eq 0) {
    if ($unverified.Count -gt 0) { 'PROBE: no rejections, but some peers do not enforce the key on /__authprobe (marked ?): not proven for them' } else { 'PROBE: ALL ACCEPTED (every peer enforced and accepted)' }
    exit 0
}
'PROBE: ' + $bad.Count + ' holder(s) have a rejected/unreachable peer (401/403 = key mismatch, down = no answer)'
exit 1
