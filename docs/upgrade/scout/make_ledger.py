"""Builds docs/upgrade/LEDGER.md from the research candidate rows. Usage: python make_ledger.py prep|build

prep   writes covered/todo-<group>.json: the adopted rows that no reference file covers, for the pass that
       checks each of them against the kit (its answers are covered/built-<group>.json).
build  writes ../LEDGER.md: LEDGER.head.md (coverage map, written by hand) followed by one table per decision.

Inputs: draft/*.candidates.jsonl (one row per candidate, written during the research of 10 to 12 Nov 2026 and
the rounds after it), covered/*.covered.json (rows a reference file documents with when, how and source),
covered/built-*.json (what the kit holds for a row, checked against its files; it outranks a reference) and
covered/tried.json (third-party tools whose enabling step was run in a throwaway environment).
"""
import collections
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
GROUPS = {"A": ["agent-standards", "platform-claude-code", "platform-codex", "platform-cursor", "prompting-guidance",
                "sweep-agent-platform"],
          "B": ["loop-autoresearch", "sweep-auto-research", "sweep-unattended-security", "unattended-security",
                "platforms", "user-reports"]}  # every other note is group C
UNDECIDED_WHY = ("not run: on 11 Nov 2026 the user limited this upgrade to the most important items "
                 "(usage limit of the session's model); the rounds after it ran under the same limit")


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def rows():
    out = []
    for f in sorted((HERE / "draft").glob("*.candidates.jsonl")):
        for line in f.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                r["_file"] = f.name[:-len(".candidates.jsonl")]
                out.append(r)
    return out


def covered():
    cov = {}
    for f in sorted((HERE / "covered").glob("*.covered.json")):
        for c in load(f):
            cov[(c["file"], c["candidate"])] = "references/%s.md (%s)" % (f.name.split(".")[0], c["section"])
    return cov


def cell(s, n=300):
    s = " ".join(str(s or "").split()).replace("|", "/")
    return s if len(s) <= n else s[:n - 1].rstrip() + "…"


def prep(all_rows, cov):
    todo = collections.defaultdict(list)
    for r in all_rows:
        if r["suggested_decision"] == "Adopt" and (r["_file"], r["candidate"]) not in cov:
            g = next((k for k, v in GROUPS.items() if r["_file"] in v), "C")
            todo[g].append({k: cell(r[k2], 420) for k, k2 in (("file", "_file"), ("candidate", "candidate"),
                            ("kind", "kind"), ("core_or_optional", "core_or_optional"), ("what", "what"),
                            ("mechanism", "mechanism"))})
    for g, items in sorted(todo.items()):
        (HERE / "covered" / ("todo-%s.json" % g)).write_text(json.dumps(items, indent=1, ensure_ascii=False) + "\n",
                                                             encoding="utf-8", newline="\n")
        print(g, len(items))
    print(collections.Counter(r["kind"] for r in all_rows if r["suggested_decision"] == "Adopt").most_common())


def tried_note(r, tried):
    """The stack-try result for a third-party tool row, or None when the row names no tried tool."""
    name = r["candidate"].lower()
    hit = [t for t in tried if any(k in name for k in t["match"])]
    return hit[0] if hit else None


def build(all_rows, cov):
    built = {}
    for f in sorted((HERE / "covered").glob("built-*.json")):
        for c in load(f):
            built[(c["file"], c["candidate"])] = c
    tp = HERE / "covered" / "tried.json"
    tried = load(tp) if tp.exists() else []
    by = collections.defaultdict(list)
    for r in sorted(all_rows, key=lambda r: (r["_file"], r["candidate"].lower())):
        by[r["suggested_decision"]].append(r)
    out = [(HERE / "LEDGER.head.md").read_text(encoding="utf-8").rstrip("\n"), ""]
    counts = collections.Counter()

    out += ["## Adopt (%d rows)" % len(by["Adopt"]), "",
            "Status says where the row is finished, or why it is not.", "",
            "| Candidate | Note | Core or optional | Status | Reason | Source | Checked |", "|---|---|---|---|---|---|---|"]
    for r in by["Adopt"]:
        key = (r["_file"], r["candidate"])
        b, t = built.get(key), tried_note(r, tried)
        if b:  # the record of what was built outranks a reference that covers the same row
            status = "%s: %s" % (b["status"], b["where"])
            counts[b["status"]] += 1
        elif key in cov and t and (t.get("any_note") or r["_file"] != "optimization-performance") and "stack.md" in cov[key]:
            status = ("finished: %s; enabling step run %s" if t["ok"] else "unfinished: documented in %s, but %s") \
                % (cov[key], t["note"])
            counts["finished" if t["ok"] else "unfinished"] += 1
        elif key in cov and "stack.md" in cov[key] and r["kind"] in ("tool", "library", "service", "framework",
                                                                    "mcp-server", "plugin", "skill", "product"):
            status = "unfinished: documented in %s, enabling step not run here" % cov[key]
            counts["unfinished"] += 1
        elif key in cov:
            status = "finished: " + cov[key]
            counts["finished"] += 1
        else:
            status = "unfinished: not checked against the kit"
            counts["unfinished"] += 1
        out.append("| %s | %s | %s | %s | %s | %s | %s |" % (cell(r["candidate"], 160), r["_file"], r["core_or_optional"],
                   cell(status, 320), cell(r["reason"]), cell(r["evidence"]), cell(r["checked"], 24)))

    for dec, title in (("Trial", "Trial: undecided, worth a test"), ("Assess", "Assess: undecided, looked at only")):
        out += ["", "## %s (%d rows)" % (title, len(by[dec])), "",
                "Each row names the test it still needs. Why it was not run, for all of them: " + UNDECIDED_WHY + ".", "",
                "| Candidate | Note | Core or optional | Test still needed | Reason | Source | Checked |", "|---|---|---|---|---|---|---|"]
        for r in by[dec]:
            out.append("| %s | %s | %s | %s | %s | %s | %s |" % (cell(r["candidate"], 160), r["_file"],
                       r["core_or_optional"], cell(r["cheap_local_trial"]), cell(r["reason"]), cell(r["evidence"]),
                       cell(r["checked"], 24)))
    for dec, title in (("Hold", "Hold: not now, with the reason"), ("Reject", "Reject")):
        out += ["", "## %s (%d rows)" % (title, len(by[dec])), "",
                "| Candidate | Note | Reason | Source | Checked |", "|---|---|---|---|---|"]
        for r in by[dec]:
            out.append("| %s | %s | %s | %s | %s |" % (cell(r["candidate"], 160), r["_file"], cell(r["reason"]),
                       cell(r["evidence"]), cell(r["checked"], 24)))
    text = "\n".join(out) + "\n"
    text = text.replace("{ADOPT_FINISHED}", str(counts["finished"])).replace("{ADOPT_UNFINISHED}", str(counts["unfinished"]))
    for dec in ("Adopt", "Trial", "Assess", "Hold", "Reject"):
        text = text.replace("{N_%s}" % dec.upper(), str(len(by[dec])))
    (HERE.parent / "LEDGER.md").write_text(text.replace("{N_ROWS}", str(len(all_rows))), encoding="utf-8", newline="\n")
    print("rows", len(all_rows), dict(counts), "bytes", len(text.encode("utf-8")))
    missing = [k for k in built if k not in {(r["_file"], r["candidate"]) for r in all_rows}]
    print("built entries that match no row:", len(missing), missing[:3])


if __name__ == "__main__":
    {"prep": prep, "build": build}[sys.argv[1]](rows(), covered())
