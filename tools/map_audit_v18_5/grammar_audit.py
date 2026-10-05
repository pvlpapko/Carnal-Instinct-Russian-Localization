"""Full-table integrity scan and a morphology-assisted editorial review queue.

Morphology creates candidates only; it never rewrites dialogue automatically.
Install pymorphy3==2.0.6 and razdel==0.5.0 outside the release workspace.
"""
from pathlib import Path
import collections, csv, functools, json, re, sys
import pymorphy3
from razdel import tokenize

ROOT, OUT = map(Path, sys.argv[1:3])
morph = pymorphy3.MorphAnalyzer()


@functools.lru_cache(maxsize=None)
def parse(word):
    return morph.parse(word.lower().replace('ё', 'е'))


def compatible(a, n):
    # Russian plural adjectives do not encode gender.
    return all(not getattr(a, x) or not getattr(n, x) or getattr(a, x) == getattr(n, x)
               for x in ('case', 'number')) and (n.number == 'plur' or not a.gender or not n.gender or a.gender == n.gender)


report = {'method': 'integrity + dictionary morphology + manual source-context review',
          'automatic_grammar_correction': False, 'editions': {}, 'agreement_candidates': [],
          'unknown_word_candidates': [], 'phrase_candidates': [], 'integrity_errors': []}
word_examples = collections.defaultdict(list)
word_counts = collections.Counter()
seen = set()
patterns = [r'\bпо крайне мере\b', r'\bвообщем\b', r'\bвобщем\b', r'\bвобще\b', r'\bиз за\b',
            r'\bиметь ввиду\b', r'\bни кто\b', r'\bне смотря на\b', r'\.{4,}', r'[!?]\.{3,}']
for folder in ROOT.glob('*/translation.tsv'):
    rows = list(csv.DictReader(folder.open(encoding='utf-8-sig', newline=''), delimiter='\t'))
    report['editions'][folder.parent.name] = {'rows_scanned': len(rows)}
    for r in rows:
        identity = [r['Namespace'], r['Key'], r['SourceStringHash']]
        en, ru = r['English'], r['Russian']
        for expression, label in [(r'\{[^{}]+\}', 'placeholders'), (r'</?[A-Za-z][^>]*>', 'markup tags')]:
            if collections.Counter(re.findall(expression, en)) != collections.Counter(re.findall(expression, ru)):
                report['integrity_errors'].append({'edition': folder.parent.name, 'identity': identity, 'type': label})
        if (en, ru) in seen:
            continue
        seen.add((en, ru))
        context = {'english': en, 'russian': ru, 'assets': r['Assets'], 'identity': identity}
        if any(re.search(p, ru, re.I) for p in patterns):
            report['phrase_candidates'].append(context)
        words = list(tokenize(ru))
        for word in words:
            if not re.fullmatch('[а-яА-ЯёЁ-]+', word.text) or len(word.text) < 3:
                continue
            norm = word.text.lower()
            word_counts[norm] += 1
            if len(word_examples[norm]) < 2:
                word_examples[norm].append(context)
        if 'loc_dlg' not in r['Assets']:
            continue
        for left, right in zip(words, words[1:]):
            if not re.fullmatch('[а-яА-ЯёЁ]+', left.text) or not re.fullmatch('[а-яА-ЯёЁ]+', right.text):
                continue
            ap, np = parse(left.text), parse(right.text)
            if ap[0].tag.POS != 'ADJF' or np[0].tag.POS != 'NOUN' or min(ap[0].score, np[0].score) < .7:
                continue
            aa = [p.tag for p in ap if p.tag.POS == 'ADJF' and p.score >= .1]
            nn = [p.tag for p in np if p.tag.POS == 'NOUN' and p.score >= .1]
            if not any(compatible(a, n) for a in aa for n in nn):
                report['agreement_candidates'].append({**context, 'phrase': left.text + ' ' + right.text})
for word, count in word_counts.most_common():
    if count >= 2 and not morph.word_is_known(word):
        report['unknown_word_candidates'].append({'word': word, 'count': count, 'examples': word_examples[word]})
report['distinct_pairs_scanned'] = len(seen)
report['distinct_russian_words'] = len(word_counts)
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'rows': sum(v['rows_scanned'] for v in report['editions'].values()),
                  'agreement_candidates': len(report['agreement_candidates']),
                  'unknown_words': len(report['unknown_word_candidates']),
                  'phrase_candidates': len(report['phrase_candidates']), 'integrity_errors': len(report['integrity_errors'])}))
