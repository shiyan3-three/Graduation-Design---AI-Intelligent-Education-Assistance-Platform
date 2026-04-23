from __future__ import annotations

import csv
import io
import os
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, TextIO

import httpx


HF_DEFAULT_ENDPOINT = 'https://huggingface.co'
DATASET_SPLITS = ('dev', 'val', 'test')
CSV_COLUMNS = ['id', 'question', 'A', 'B', 'C', 'D', 'answer', 'explanation']
OUTPUT_DIR = Path(__file__).resolve().parent / 'ceval_data'
SUBJECTS: Mapping[str, str] = {
    'high_school_mathematics': '高中数学',
    'high_school_physics': '高中物理',
    'high_school_chemistry': '高中化学',
    'middle_school_mathematics': '初中数学',
    'middle_school_physics': '初中物理',
    'middle_school_chemistry': '初中化学',
    'high_school_biology': '高中生物',
}


def build_parquet_url(subject: str, split: str) -> str:
    endpoint = os.getenv('HF_ENDPOINT', HF_DEFAULT_ENDPOINT).strip() or HF_DEFAULT_ENDPOINT
    endpoint = endpoint.rstrip('/')
    return (
        f'{endpoint}/datasets/ceval/ceval-exam/resolve/main/'
        f'{subject}/{split}-00000-of-00001.parquet'
    )


def run(
    output_dir: Path = OUTPUT_DIR,
    stdout: TextIO = sys.stdout,
) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    completed_subjects = 0

    with httpx.Client(timeout=60.0, follow_redirects=True) as client:
        for subject, subject_name in SUBJECTS.items():
            print(f'[C-Eval] 开始处理 {subject_name} ({subject})', file=stdout)
            try:
                row_count = download_subject_dataset(
                    client=client,
                    subject=subject,
                    output_dir=output_dir,
                    stdout=stdout,
                )
            except Exception as exc:  # noqa: BLE001 - one failed subject must not abort the whole batch
                print(
                    f'[C-Eval] 警告：{subject} 下载失败，已跳过。原因：{exc}',
                    file=stdout,
                )
                continue

            completed_subjects += 1
            print(
                f'[C-Eval] 完成 {subject}，成功写入 {row_count} 道题。',
                file=stdout,
            )

    print(
        f'[C-Eval] 处理结束，共成功导出 {completed_subjects} 个学科。',
        file=stdout,
    )
    return completed_subjects


def download_subject_dataset(
    client: httpx.Client,
    subject: str,
    output_dir: Path,
    stdout: TextIO = sys.stdout,
) -> int:
    rows: List[Dict[str, str]] = []

    for split in DATASET_SPLITS:
        print(f'[C-Eval] 正在下载 {subject} / {split}', file=stdout)
        split_rows = normalize_records(
            download_parquet_rows(client=client, subject=subject, split=split)
        )
        rows.extend(split_rows)
        print(
            f'[C-Eval] {subject} / {split} 已读取 {len(split_rows)} 道有效题。',
            file=stdout,
        )

    output_path = output_dir / f'{subject}.csv'
    write_csv(output_path, rows)
    return len(rows)


def download_parquet_rows(
    client: httpx.Client,
    subject: str,
    split: str,
) -> List[Dict[str, str]]:
    url = build_parquet_url(subject, split)
    response = client.get(url)
    response.raise_for_status()
    return parse_parquet_rows(response.content)


def parse_parquet_rows(payload: bytes) -> List[Dict[str, str]]:
    try:
        import pandas as pd
    except ImportError as exc:  # pragma: no cover - depends on runtime environment
        raise RuntimeError('读取 parquet 需要先安装 pandas 和 pyarrow。') from exc

    frame = pd.read_parquet(io.BytesIO(payload), engine='pyarrow')
    records = frame.to_dict(orient='records')
    return normalize_records(records)


def normalize_records(records: Iterable[Mapping[str, Any]]) -> List[Dict[str, str]]:
    normalized: List[Dict[str, str]] = []

    for record in records:
        answer = str(record.get('answer') or '').strip()
        if not answer:
            continue

        normalized.append(
            {
                'id': _stringify(record.get('id')),
                'question': _stringify(record.get('question')),
                'A': _stringify(record.get('A')),
                'B': _stringify(record.get('B')),
                'C': _stringify(record.get('C')),
                'D': _stringify(record.get('D')),
                'answer': answer,
                'explanation': _stringify(record.get('explanation')),
            }
        )

    return normalized


def write_csv(output_path: Path, rows: Iterable[Mapping[str, str]]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, '') for column in CSV_COLUMNS})


def _stringify(value: Any) -> str:
    if value is None:
        return ''
    return str(value).strip()


def main() -> int:
    completed = run()
    return 0 if completed > 0 else 1


if __name__ == '__main__':
    raise SystemExit(main())
