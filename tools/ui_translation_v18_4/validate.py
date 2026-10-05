"""Independent readback of the shipped localization and UI property changes."""
from pathlib import Path
import sys, json, csv, hashlib, collections, re, zlib
import ui_properties as ui
from ci_formats import Toc, Locres, parse_pak_one, zen_info

root, base, sources = map(Path, sys.argv[1:4])
report = {"release": "18.4", "runtime_tested": False, "editions": {}}


def source_hash(text):
    return zlib.crc32(text.encode("utf-32-le")) & 0xffffffff


def read_script_string(data, pos):
    opcode = data[pos]
    pos += 1
    if opcode == 0x1f:
        end = data.index(b"\0", pos)
        return data[pos:end].decode("ascii"), end + 1
    if opcode == 0x34:
        end = pos
        while data[end:end + 2] != b"\0\0":
            assert end + 2 <= len(data)
            end += 2
        return data[pos:end].decode("utf-16-le"), end + 2
    raise ValueError("not a string constant")


def script_texts(data):
    for match in re.finditer(re.escape(b"\x29\x01"), data):
        try:
            source, pos = read_script_string(data, match.end())
            key, pos = read_script_string(data, pos)
            namespace, pos = read_script_string(data, pos)
            yield namespace, key, source
        except (ValueError, IndexError, UnicodeError, AssertionError):
            continue


for edition in ("Steam_current", "NoSteam_0.7.9.16232"):
    folder = root / "Data" / edition
    rows = list(csv.DictReader((folder / "translation.tsv").open(encoding="utf-8-sig", newline=""), delimiter="\t"))
    loc = Locres(folder / "Game.locres")
    original = Locres(base / "Data" / edition / "Game.locres")
    indexed = {(e["namespace"], e["key"], str(e["source_hash"])): e for e in loc.entries}
    assert len(indexed) == len(loc.entries), "duplicate localization identities"
    assert [(e["namespace"], e["key"], e["source_hash"], e["key_hash"], e["namespace_hash"]) for e in original.entries] == [
        (e["namespace"], e["key"], e["source_hash"], e["key_hash"], e["namespace_hash"]) for e in loc.entries[:len(original.entries)]]
    fallback_rows = []
    for row in rows:
        assert row["Russian"], row["Key"]
        assert collections.Counter(re.findall(r"\{[^{}]+\}", row["English"])) == collections.Counter(re.findall(r"\{[^{}]+\}", row["Russian"])), row["Key"]
        variants = (row["English"], row["English"].replace("\r\n", "\n").replace("\n", "\r\n"))
        assert int(row["SourceStringHash"]) in [source_hash(v) for v in variants], row["Key"]
        entry = indexed.get((row["Namespace"], row["Key"], row["SourceStringHash"]))
        if entry:
            assert entry["value"].replace("\r\n", "\n") == row["Russian"].replace("\r\n", "\n"), row["Key"]
        else:
            assert "exact FText local fallback" in row["SourceEvidence"]
            fallback_rows.append(row)
    parsed_pak = parse_pak_one(root / "Files" / edition / "pakchunk1015-Windows_P.pak")
    assert parsed_pak["data"] == (folder / "Game.locres").read_bytes()
    toc = Toc(root / "Files" / edition / "pakchunk1015-Windows_P.utoc")
    old_toc = Toc(base / "Files" / edition / "pakchunk1015-Windows_P.utoc")
    previous = {mount: old_toc.read_chunk(index) for mount, index in old_toc.files}
    files = {mount: toc.read_chunk(index) for mount, index in toc.files}
    output = root / "VerifiedExtracted" / edition
    toc.extract_named(output)
    assert not toc.verify_meta()
    assert sum(b[1] for b in toc.blocks) == len(toc.ub)
    function_exports = 0
    for mount, data in files.items():
        original_data = previous.get(mount)
        if original_data is None:
            original_data = (sources / mount.removeprefix("Carnal_Instinct_UE5/")).read_bytes()
        op = output / mount
        sp = root / "Developer/V18_4/validation-source" / edition / mount
        sp.parent.mkdir(parents=True, exist_ok=True)
        sp.write_bytes(original_data)
        p, q = ui.zen.package(sp), ui.zen.package(op)
        assert p["name"] == q["name"] and len(p["exports"]) == len(q["exports"]), mount
        assert zen_info(original_data)["imports"] == zen_info(data)["imports"], mount
        assert q["names"][:len(p["names"])] == p["names"], mount
        for a, b in zip(p["exports"], q["exports"]):
            assert (a["name"], a["cls"], a["outer"], a["template"], a["super"], a["flags"]) == (
                b["name"], b["cls"], b["outer"], b["template"], b["super"], b["flags"]), mount
            if a["cls"] == 0x574f27aec05072d0:
                assert original_data[a["start"]:a["end"]] == data[b["start"]:b["end"]], (mount, a["name"])
                function_exports += 1
    for name in ("WB_QuestObjectiveName", "WB_QuestObjectiveDescription"):
        path = next(output.rglob(name + ".uasset"))
        text = next(e for e in ui.describe(path) if e["name"] == "Text_ObjectiveName")
        assert "error" not in text, text
        props = text["properties"]
        assert props["AutoWrapText"]["value"] == 1
        assert props["Font"]["value"]["Size"]["value"] == 20.0
        assert "Italic" not in props["Font"]["value"]["TypefaceFontName"]["value"]
    stats = ui.describe(next(output.rglob("WB_Stats_Full.uasset")))
    column = next(e for e in stats if e["name"] == "Column1")
    assert column["properties"]["WidthOverride"]["value"] == 512.0
    screen = ui.describe(next(output.rglob("WB_CharacterScreen.uasset")))
    assert next(e for e in screen if e["name"] == "StatsSize")["properties"]["WidthOverride"]["value"] == 1198.0
    map_texts = []
    for mount, data in files.items():
        if "/dmap_system/" in mount or "/UI/WorldMap/" in mount:
            map_texts.extend(script_texts(data))
    if edition == "Steam_current":
        # The current game's popup already contains its own display localizer;
        # confirm its coverage without replacing its bytecode.
        map_texts.extend(script_texts(next(sources.rglob("WB_WorldMapPopup.uasset")).read_bytes()))
    unresolved = []
    for ns, key, source in map_texts:
        if ns.startswith("CI_RU_Display_"):
            entry = indexed.get((ns, key, str(source_hash(source))))
            if not entry or not entry["value"]:
                unresolved.append((ns, key, source))
    assert not unresolved, unresolved[:3]
    if edition == "Steam_current":
        assert len([e for e in loc.entries if e["namespace"] == "CI_RU_Display_V18_4_Items"]) == 3
        item = next(output.rglob("Essence_Tier_1_Small.uasset")).read_bytes()
        assert item.count(__import__("ci_formats").fstring_write("CI_RU_Display_V18_4_Items")) == 3
    else:
        assert not any(mount.endswith("Essence_Tier_1_Small.uasset") for mount in files)
    report["editions"][edition] = {"translation_rows": len(rows), "locres_entries": len(loc.entries),
                                   "source_hashes": "PASS", "placeholders": "PASS", "pak_readback": "PASS",
                                   "packages": len(files), "toc_hashes": "PASS", "gameplay_function_exports_unchanged": function_exports,
                                   "map_display_ftext_occurrences_checked": len(map_texts), "unresolved_map_display_texts": 0,
                                   "journal_wrapping_font_and_character_width": "PASS", "legacy_exact_fallback_rows": len(fallback_rows)}
(root / "Reports/V18_4_VALIDATION.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
print(json.dumps(report, ensure_ascii=False, indent=2))
