"""Bounded native Base FText decoding; empty FString may occupy 4 or 5 bytes."""
from dataclasses import dataclass
import re, struct

@dataclass(frozen=True)
class BaseFText:
    start: int
    end: int
    flags: int
    namespace: str
    key: str
    source: str
    namespace_start: int
    namespace_end: int


def fstring(data, pos):
    if pos < 0 or pos + 4 > len(data):
        raise ValueError('FString length outside export')
    count = struct.unpack_from('<i', data, pos)[0]
    start = pos + 4
    size = count if count >= 0 else -count * 2
    if size > len(data) - start:
        raise ValueError(f'FString length {count} exceeds export at {pos}')
    if not count:
        return '', start
    raw = data[start:start + size]
    terminator = b'\0' if count > 0 else b'\0\0'
    if not raw.endswith(terminator):
        raise ValueError('FString missing terminator')
    return raw[:-len(terminator)].decode('utf-8' if count > 0 else 'utf-16-le'), start + size


def read_base(data, start):
    if start < 0 or start + 5 > len(data):
        raise ValueError('FText outside export')
    flags = struct.unpack_from('<I', data, start)[0]
    if data[start + 4] != 0:
        raise ValueError('not Base FText history')
    ns_start = start + 5
    namespace, ns_end = fstring(data, ns_start)
    key, pos = fstring(data, ns_end)
    source, end = fstring(data, pos)
    return BaseFText(start, end, flags, namespace, key, source, ns_start, ns_end)


def guid_base_texts(data):
    """Find complete records, validating their boundaries rather than substrings."""
    found = {}
    for match in re.finditer(rb'\x21\0\0\0[0-9A-Fa-f]{32}\0', data):
        key_pos = match.start()
        # Namespace may be empty or a bounded ASCII/UTF16 string.
        for ns_start in range(max(5, key_pos - 1024), key_pos - 3):
            try:
                value, end = fstring(data, ns_start)
                if end != key_pos:
                    continue
                record = read_base(data, ns_start - 5)
                if record.namespace != value or record.flags & ~0xff:
                    continue
                found[record.start] = record
            except (ValueError, UnicodeError, struct.error):
                continue
    return list(sorted(found.values(), key=lambda x: x.start))


def replace_namespace(data, record, namespace, write_fstring):
    assert read_base(data, record.start) == record
    raw = data[record.start:record.end]
    encoded = raw[:5] + write_fstring(namespace) + data[record.namespace_end:record.end]
    result = read_base(encoded, 0)
    assert result.end == len(encoded)
    assert (result.flags, result.key, result.source) == (record.flags, record.key, record.source)
    assert result.namespace == namespace
    return encoded
