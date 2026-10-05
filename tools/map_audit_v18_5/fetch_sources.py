"""Resumable read-only acquisition of shipped map cells and display data.

The source index is navigation metadata, not proof of live file hashes.
Download independent small files, save a hash for each, and retry only failed units.
"""
from pathlib import Path
import sys, json, concurrent.futures, urllib.request, hashlib, time, threading

index_path, out = map(Path, sys.argv[1:3])
entries = json.loads(index_path.read_text())["entries"]
targets = [f for f in entries if f["type"] == "file" and (
    (f["relative_path"].endswith(".umap") and "/Maps/Shipping/" in f["relative_path"])
    or (f["relative_path"].endswith(".uasset") and any(p in f["relative_path"] for p in (
        "/dqst_system/common/", "/dmap_system/common/", "/Classes/Interactable/Campfires/")))
)]
out.mkdir(parents=True, exist_ok=True)
manifest_path = out / "SOURCE_READBACK.jsonl"
known = {}
if manifest_path.exists():
    for line in manifest_path.read_text().splitlines():
        record = json.loads(line)
        if "sha256" in record:
            known[record["relative_path"]] = record
pending = [f for f in targets if f["relative_path"] not in known or not (out / f["relative_path"]).exists()]
lock = threading.Lock()
done = len(targets) - len(pending)


def fetch(f):
    p = out / f["relative_path"]
    p.parent.mkdir(parents=True, exist_ok=True)
    record = {"relative_path": f["relative_path"], "drive_id": f["drive_id"]}
    for attempt in range(3):
        try:
            if p.exists():
                data = p.read_bytes()
            else:
                with urllib.request.urlopen("https://drive.google.com/uc?export=download&id=" + f["drive_id"], timeout=20) as response:
                    data = response.read()
                assert data and data[:1] != b"<", "Drive returned HTML"
                temp = p.with_suffix(p.suffix + ".partial")
                temp.write_bytes(data)
                temp.replace(p)
            record.update(bytes=len(data), sha256=hashlib.sha256(data).hexdigest(), index_sha256=f.get("sha256"))
            break
        except Exception as error:
            if attempt == 2:
                record["error"] = str(error)
            else:
                time.sleep(2 * (attempt + 1))
    global done
    with lock:
        with manifest_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")
        done += 1
        if done % 100 == 0 or done == len(targets):
            print(json.dumps({"downloaded_or_attempted": done, "target_files": len(targets)}, ensure_ascii=False), flush=True)
    return record


print(json.dumps({"targets": len(targets), "already_acquired": done, "pending": len(pending)}), flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
    results = list(pool.map(fetch, pending))
errors = [r for r in results if "error" in r]
summary = {"target_files": len(targets), "new_success": len(results) - len(errors), "failures": errors,
           "source_index_sha256": hashlib.sha256(index_path.read_bytes()).hexdigest()}
(out / "DOWNLOAD_STATE.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
print(json.dumps({"target_files": len(targets), "new_success": len(results) - len(errors), "failure_count": len(errors)}, ensure_ascii=False), flush=True)
