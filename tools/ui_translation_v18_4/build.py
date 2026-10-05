"""Display-only v18.4 changes, applied to separate verified v18.3 payloads.

Usage: python build.py RELEASE_WORKSPACE CURRENT_UI_SOURCE
The workspace is a copy of the canonical v18.3 archive. Original sources are read-only.
"""
from pathlib import Path
import sys, csv, json, struct, hashlib, re, collections, zlib
import ui_properties as ui
from ci_formats import Toc, Locres, build_pak_one
import ci_formats as cf
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from native_ftext import guid_base_texts, replace_namespace

ROOT = Path(sys.argv[1])
SOURCE = Path(sys.argv[2])
BASE = Path(sys.argv[3]) if len(sys.argv) > 3 else ROOT
REPORT = {"release": "18.4", "runtime_tested": False, "editions": {}, "changes": []}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def header(properties):
    """Serialize explicit native property indices, preserving zero-valued fields."""
    out = bytearray()
    cursor = 0
    zero_count = 0
    for position, (index, zero) in enumerate(properties):
        skip = index - cursor
        while skip > 127:
            out += struct.pack("<H", 127)
            cursor += 127
            skip -= 127
        out += struct.pack("<H", skip | (128 if zero else 0) | 512 |
                           (256 if position == len(properties) - 1 else 0))
        cursor = index + 1
        zero_count += zero
    if zero_count:
        count = 1 if zero_count <= 8 else 2 if zero_count <= 16 else ((zero_count + 31) // 32) * 4
        out += ((1 << zero_count) - 1).to_bytes(count, "little")
    return bytes(out)


class WidgetPatch:
    def __init__(self, data, edition, mount):
        self.edition, self.mount = edition, mount
        self.path = ROOT / "Developer/V18_4/inputs" / edition / mount
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_bytes(data)
        self.package = ui.zen.package(self.path)
        self.changed = {}
        self.new_names = []
        self.evidence = []

    def parse(self, export):
        raw = self.changed.get(export["index"], self.package["bytes"][export["start"]:export["end"]])
        cls = "/Script/UMG." + ui.CLASS[export["cls"]]
        properties, end = ui.obj(raw, 0, cls, self.package["names"] + self.new_names)
        assert raw[end:] == b"\0" * 4, (self.mount, export["name"], raw[end:].hex())
        return raw, properties, cls

    def set(self, export, path, value, fmt="f"):
        raw, properties, cls = self.parse(export)
        parts = path.split(".")
        field = properties.get(parts[0])
        if field is None:
            assert len(parts) == 1, (self.mount, path)
            fs = ui.fields(cls)
            index = next(i for i, f in enumerate(fs) if f["name"] == path)
            assert fs[index]["type"] in ("BoolProperty", "FloatProperty", "ByteProperty")
            items = sorted([(v["index"], v["zero"], raw[v["start"]:v["end"]])
                            for v in properties.values()] + [(index, False, struct.pack("<" + fmt, value))])
            raw = header([(i, z) for i, z, _ in items]) + b"".join(b for _, _, b in items) + b"\0" * 4
            old = "native default"
        else:
            for part in parts[1:]:
                field = field["value"][part]
            old = field["value"]
            if old == value:
                return
            assert not field["zero"], (self.mount, export["name"], path)
            encoded = struct.pack("<" + fmt, *value) if isinstance(value, tuple) else struct.pack("<" + fmt, value)
            assert len(encoded) == field["end"] - field["start"], (path, field)
            raw = raw[:field["start"]] + encoded + raw[field["end"]:]
        self.changed[export["index"]] = raw
        self.evidence.append({"export": export["name"], "export_index": export["index"],
                              "property": path, "old": old, "new": value})
        self.parse(export)

    def select(self, name):
        hits = [e for e in self.package["exports"] if e["name"] == name]
        assert len(hits) == 1, (self.mount, name)
        return hits[0]

    def finish(self):
        p = self.package
        data = ui.zen.rebuild(p, self.changed, self.new_names)
        output = ROOT / "Developer/V18_4/patched" / self.edition / self.mount
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(data)
        q = ui.zen.package(output)
        assert p["name"] == q["name"] and len(p["exports"]) == len(q["exports"])
        assert q["names"][:len(p["names"])] == p["names"]
        oldinfo, newinfo = cf.zen_info(p["bytes"]), cf.zen_info(data)
        assert oldinfo["imports"] == newinfo["imports"]
        for a, b in zip(p["exports"], q["exports"]):
            assert (a["name"], a["cls"], a["outer"], a["super"], a["template"], a["flags"]) == (
                b["name"], b["cls"], b["outer"], b["super"], b["template"], b["flags"])
            if a["index"] not in self.changed:
                assert p["bytes"][a["start"]:a["end"]] == data[b["start"]:b["end"]]
        assert q["header"][1] == p["header"][1] or q["header"][1] < 65536, (self.mount, q["header"][1])
        REPORT["changes"].append({"edition": self.edition, "mount": self.mount,
                                 "source_sha256": sha(p["bytes"]), "patched_sha256": sha(data),
                                 "source_header": p["header"][1], "patched_header": q["header"][1],
                                 "imports_unchanged": True, "function_exports_unchanged": True,
                                 "evidence": self.evidence})
        return data


TEXT_UPDATES = {
    "Refresh Toy List": "Обновить список",
    "Restore Defaults": "Сбросить",
    "Restore Defaults\n{section}": "Сбросить настройки\n{section}",
    "Restore Defaults\nAll Sections": "Сбросить настройки\nВсе разделы",
    "Device Port Override": "Порт устройства",
    "Device IP Override": "IP-адрес устройства",
}


def item_display_namespace(edition, rows, loc):
    """Resolve three conflicting item texts without changing item identifiers."""
    if edition != "Steam_current":
        return
    suffix = "RPG_InventorySystem/Classes/MainItemClasses/Consumables/Essence/Essence_Tier_1_Small.uasset"
    targets = [r for r in rows if r["Assets"] == suffix and "exact FText local fallback" in r["SourceEvidence"]]
    assert len(targets) == 3
    source = SOURCE / "Content" / suffix
    p = WidgetPatch(source.read_bytes(), edition, "Carnal_Instinct_UE5/Content/" + suffix)
    namespace = "CI_RU_Display_V18_4_Items"
    def key_hash(s):
        if not s:
            return 0
        h = cf.CityHash64(s.encode("utf-16-le"))
        return ((h & 0xffffffff) + (h >> 32) * 23) & 0xffffffff
    additions = []
    for row in targets:
        hits = 0
        actual_source = None
        variants = dict.fromkeys((row["English"], row["English"].replace("\r\n", "\n").replace("\n", "\r\n")))
        for export in p.package["exports"]:
            raw = p.changed.get(export["index"], p.package["bytes"][export["start"]:export["end"]])
            for english in variants:
                records = [text for text in guid_base_texts(raw)
                           if text.namespace == "" and text.key == row["Key"] and text.source == english]
                if records:
                    assert export["name"].startswith("Default__"), export["name"]
                    for text in reversed(records):
                        new = replace_namespace(raw, text, namespace, cf.fstring_write)
                        raw = raw[:text.start] + new + raw[text.end:]
                    p.changed[export["index"]] = raw
                    hits += len(records)
                    actual_source = english
            
        assert hits == 1, (row["Key"], hits)
        source_hash = zlib.crc32(actual_source.encode("utf-32-le")) & 0xffffffff
        assert source_hash == int(row["SourceStringHash"])
        assert key_hash(row["Key"]) == int(row["KeyHash"])
        loc.entries.append({"namespace": namespace, "key": row["Key"], "source_hash": source_hash,
                            "namespace_hash": key_hash(namespace), "key_hash": int(row["KeyHash"]), "value": row["Russian"]})
        additions.append({**row, "Namespace": namespace, "NamespaceHash": str(key_hash(namespace)),
                          "English": actual_source, "SourceEvidence": "v18.4 verified current-source item display namespace; original item identifiers and English retained"})
        p.evidence.append({"export": "Default__Essence_Tier_1_Small_C", "property": "FText.Namespace",
                           "key": row["Key"], "english": actual_source, "russian": row["Russian"],
                           "old": "", "new": namespace})
    rows.extend(additions)
    ITEM_OVERRIDES[p.mount] = p.finish()


ITEM_OVERRIDES = {}


def update_translation(edition):
    folder = ROOT / "Data" / edition
    path = folder / "translation.tsv"
    with (BASE / "Data" / edition / "translation.tsv").open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        rows, fields = list(reader), reader.fieldnames
    loc = Locres(BASE / "Data" / edition / "Game.locres")
    indexed = {(e["namespace"], e["key"], str(e["source_hash"])): e for e in loc.entries}
    identities = [(e["namespace"], e["key"], e["source_hash"], e["namespace_hash"], e["key_hash"]) for e in loc.entries]
    updated = []
    for row in rows:
        target = TEXT_UPDATES.get(row["English"])
        if target is None or row["Russian"] == target:
            continue
        identity = (row["Namespace"], row["Key"], row["SourceStringHash"])
        assert identity in indexed, identity
        assert collections.Counter(re.findall(r"\{[^{}]+\}", row["English"])) == collections.Counter(re.findall(r"\{[^{}]+\}", target))
        updated.append({"namespace": row["Namespace"], "key": row["Key"], "english": row["English"], "old": row["Russian"], "new": target})
        row["Russian"] = target
        indexed[identity]["value"] = target
    item_display_namespace(edition, rows, loc)
    loc.write(folder / "Game.locres")
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    new = Locres(folder / "Game.locres")
    assert identities == [(e["namespace"], e["key"], e["source_hash"], e["namespace_hash"], e["key_hash"]) for e in new.entries[:len(identities)]]
    assert all(row["Russian"] for row in rows)
    assert all(collections.Counter(re.findall(r"\{[^{}]+\}", row["English"])) ==
               collections.Counter(re.findall(r"\{[^{}]+\}", row["Russian"])) for row in rows)
    REPORT["editions"][edition] = {"translation_rows": len(rows), "locres_entries": len(new.entries),
                                    "existing_identities_preserved": True, "placeholders": "PASS", "text_updates": updated}
    build_pak_one((folder / "Game.locres").read_bytes(),
                  "Carnal_Instinct_UE5/Content/Localization/Game/en/Game.locres",
                  ROOT / "Files" / edition / "pakchunk1015-Windows_P.pak")


for edition in ("Steam_current", "NoSteam_0.7.9.16232"):
    update_translation(edition)
    toc = Toc(BASE / "Files" / edition / "pakchunk1015-Windows_P.utoc")
    files = {mount: toc.read_chunk(index) for mount, index in toc.files}
    if edition == "Steam_current":
        files.update(ITEM_OVERRIDES)

    def patch_for(name, allow_source=False):
        candidates = [mount for mount in files if Path(mount).name == name + ".uasset"]
        if candidates:
            mount = candidates[0]
            return WidgetPatch(files[mount], edition, mount)
        assert allow_source and edition == "Steam_current", (edition, name)
        source = list(SOURCE.rglob(name + ".uasset"))
        assert len(source) == 1, name
        mount = "Carnal_Instinct_UE5/" + source[0].relative_to(SOURCE).as_posix()
        return WidgetPatch(source[0].read_bytes(), edition, mount)

    p = patch_for("WB_CharacterScreen")
    p.set(p.select("SizeBox_161"), "WidthOverride", 600.0)
    p.set(p.select("StatsSize"), "WidthOverride", 1198.0)
    if p.changed:
        files[p.mount] = p.finish()

    p = patch_for("WB_Stats_Full", allow_source=True)
    for name, width in (("Column1", 512.0), ("Column2", 584.0), ("SizeBox_31", 1168.0), ("SizeBox_38", 1168.0)):
        p.set(p.select(name), "WidthOverride", width)
    for export in p.package["exports"]:
        if ui.CLASS.get(export["cls"]) == "SizeBox":
            _, props, _ = p.parse(export)
            if props.get("WidthOverride", {}).get("value") == 320.0:
                p.set(export, "WidthOverride", 370.0)
    if p.changed:
        files[p.mount] = p.finish()

    p = patch_for("WB_Stats_Main_Slot", allow_source=True)
    if any(e["name"] == "SizeBox_0" for e in p.package["exports"]):
        p.set(p.select("SizeBox_0"), "WidthOverride", 250.0)
    p.set(p.select("SizeBox_25"), "WidthOverride", 550.0)
    if p.changed:
        files[p.mount] = p.finish()

    for name in ("WB_QuestObjectiveName", "WB_QuestObjectiveDescription"):
        p = patch_for(name)
        text = p.select("Text_ObjectiveName")
        p.set(text, "Font.Size", 20.0)
        p.set(text, "AutoWrapText", 1, "B")
        if edition == "Steam_current" and name == "WB_QuestObjectiveDescription":
            names = p.package["names"]
            if "Barlow-Regular" not in names:
                p.new_names.append("Barlow-Regular")
            index = (names + p.new_names).index("Barlow-Regular")
            # Modify the serialized FName field; never rename a global name-map entry.
            p.set(text, "Font.TypefaceFontName", (index, 0), "II")
        files[p.mount] = p.finish()

    p = patch_for("WB_QuestName")
    p.set(p.select("SizeBox_27"), "WidthOverride", 550.0)
    p.set(p.select("SizeBox_27"), "HeightOverride", 128.0)
    p.set(p.select("Text_QuestName"), "AutoWrapText", 1, "B")
    if p.changed:
        files[p.mount] = p.finish()

    if edition == "Steam_current":
        p = patch_for("WB_T3_Lovense", allow_source=True)
        p.set(p.select("SizeBox_0"), "WidthOverride", 1440.0)
        for export in p.package["exports"]:
            if ui.CLASS.get(export["cls"]) == "HorizontalBoxSlot":
                _, props, _ = p.parse(export)
                padding = props.get("Padding", {}).get("value", {})
                if padding.get("Left", {}).get("value") == 8.0 and padding.get("Right", {}).get("value") == 8.0:
                    p.set(export, "Padding.Left", 20.0)
                    p.set(export, "Padding.Right", 20.0)
        files[p.mount] = p.finish()

        p = patch_for("WB_T3_NSM_Button", allow_source=True)
        p.set(p.select("T_Title"), "Font.LetterSpacing", 75, "i")
        p.set(p.select("T_Title"), "AutoWrapText", 1, "B")
        files[p.mount] = p.finish()

    # ci_formats' archived build helper passes (path,index), while its directory
    # serializer accepts (index,path). Keep the corrected v18.3 container format.
    original_directory = cf.build_directory
    cf.build_directory = lambda pairs, mount="../../../": original_directory([(index, path) for path, index in pairs], mount)
    try:
        info = cf.build_container(list(files.items()), ROOT / "Files" / edition / "pakchunk1015-Windows_P.utoc")
    finally:
        cf.build_directory = original_directory
    check = Toc(ROOT / "Files" / edition / "pakchunk1015-Windows_P.utoc")
    assert len(check.files) == len(files)
    assert all(check.read_chunk(index) == files[mount] for mount, index in check.files)
    assert not check.verify_meta()
    assert sum(block[1] for block in check.blocks) == len(check.ub)
    REPORT["editions"][edition].update(container=info, exact_readback=f"{len(files)}/{len(files)} PASS", toc_hashes="PASS")

(ROOT / "Reports/V18_4_DISPLAY_LAYOUT.json").write_text(json.dumps(REPORT, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"editions": REPORT["editions"], "modified_assets": len(REPORT["changes"])}, ensure_ascii=False, indent=2))
