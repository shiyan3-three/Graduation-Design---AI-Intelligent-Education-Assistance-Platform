from __future__ import annotations

import csv
import sys
from pathlib import Path
from typing import Iterable, Mapping, TextIO

if __package__ in {None, ''}:
    sys.path.append(str(Path(__file__).resolve().parents[2]))

from backend import database


DEFAULT_DATA_DIR = Path(__file__).resolve().parent / 'ceval_data'
KNOWN_TOPIC_KEYWORDS = (
    '勾股定理',
    '二次函数',
    '一次函数',
    '牛顿第一定律',
    '牛顿第二定律',
    '牛顿第三定律',
    '欧姆定律',
    '热力学第一定律',
    '质量守恒定律',
    '氧化还原反应',
    '离子反应',
    '化学平衡',
    '光合作用',
    '细胞呼吸',
    '遗传定律',
)


def import_ceval_directory(
    data_dir: Path = DEFAULT_DATA_DIR,
    stdout: TextIO = sys.stdout,
) -> int:
    database.init_database()
    total_imported = 0

    for csv_path in sorted(data_dir.glob('*.csv')):
        imported = import_subject_csv(csv_path)
        total_imported += imported
        print(f'[C-Eval] 已导入 {csv_path.name}: {imported} 道题', file=stdout)

    print(f'[C-Eval] 题库导入完成，共导入 {total_imported} 道题。', file=stdout)
    return total_imported


def import_subject_csv(csv_path: Path) -> int:
    subject = csv_path.stem
    with csv_path.open('r', encoding='utf-8-sig', newline='') as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)

    imported = 0
    connection = database.get_connection()
    try:
        connection.execute('DELETE FROM question_bank WHERE subject = ?', (subject,))
        for row in rows:
            normalized = normalize_csv_row(subject, row)
            if normalized is None:
                continue

            connection.execute(
                """
                INSERT INTO question_bank (
                    subject, topic, question, option_a, option_b, option_c, option_d,
                    answer, explanation, source
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    normalized['subject'],
                    normalized['topic'],
                    normalized['question'],
                    normalized['option_a'],
                    normalized['option_b'],
                    normalized['option_c'],
                    normalized['option_d'],
                    normalized['answer'],
                    normalized['explanation'],
                    normalized['source'],
                ),
            )
            imported += 1
        connection.commit()
    finally:
        connection.close()

    return imported


def normalize_csv_row(subject: str, row: Mapping[str, str]) -> dict[str, str] | None:
    question = str(row.get('question') or '').strip()
    answer = str(row.get('answer') or '').strip()
    if not question or not answer:
        return None

    return {
        'subject': subject,
        'topic': extract_topic(subject, question),
        'question': question,
        'option_a': str(row.get('A') or '').strip(),
        'option_b': str(row.get('B') or '').strip(),
        'option_c': str(row.get('C') or '').strip(),
        'option_d': str(row.get('D') or '').strip(),
        'answer': answer,
        'explanation': str(row.get('explanation') or '').strip(),
        'source': 'ceval',
    }


def extract_topic(subject: str, question: str) -> str:
    for keyword in KNOWN_TOPIC_KEYWORDS:
        if keyword in question:
            return keyword
    return subject


def main() -> int:
    import_ceval_directory()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
