from __future__ import annotations

import csv
import io
import os
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

from backend.tools.download_ceval import (
    CSV_COLUMNS,
    build_parquet_url,
    download_subject_dataset,
    run,
)


class DownloadCevalTests(unittest.TestCase):
    def test_build_parquet_url_uses_hf_endpoint_when_present(self) -> None:
        with patch.dict(os.environ, {'HF_ENDPOINT': 'https://hf-mirror.com'}, clear=False):
            url = build_parquet_url('high_school_mathematics', 'dev')

        self.assertEqual(
            'https://hf-mirror.com/datasets/ceval/ceval-exam/resolve/main/'
            'high_school_mathematics/dev-00000-of-00001.parquet',
            url,
        )

    def test_download_subject_dataset_merges_splits_and_filters_missing_answer_rows(self) -> None:
        output_dir = Path('project-scipt/runtime/test-download-ceval') / str(uuid4())
        output_dir.mkdir(parents=True, exist_ok=True)

        with patch(
            'backend.tools.download_ceval.download_parquet_rows',
            side_effect=[
                [
                    {
                        'id': 1,
                        'question': '题目 1',
                        'A': 'A1',
                        'B': 'B1',
                        'C': 'C1',
                        'D': 'D1',
                        'answer': 'A',
                        'explanation': '解析 1',
                    },
                    {
                        'id': 2,
                        'question': '题目 2',
                        'A': 'A2',
                        'B': 'B2',
                        'C': 'C2',
                        'D': 'D2',
                        'answer': '',
                        'explanation': '解析 2',
                    },
                ],
                [
                    {
                        'id': 3,
                        'question': '题目 3',
                        'A': 'A3',
                        'B': 'B3',
                        'C': 'C3',
                        'D': 'D3',
                        'answer': 'C',
                        'explanation': '解析 3',
                    }
                ],
                [],
            ],
        ):
            row_count = download_subject_dataset(
                client=MagicMock(),
                subject='high_school_mathematics',
                output_dir=output_dir,
            )

        output_file = output_dir / 'high_school_mathematics.csv'
        self.assertEqual(2, row_count)
        self.assertTrue(output_file.exists())

        with output_file.open('r', encoding='utf-8-sig', newline='') as handle:
            rows = list(csv.DictReader(handle))

        self.assertEqual(CSV_COLUMNS, list(rows[0].keys()))
        self.assertEqual(['1', '3'], [row['id'] for row in rows])
        self.assertEqual(['A', 'C'], [row['answer'] for row in rows])

    def test_run_skips_failed_subjects_without_crashing(self) -> None:
        output_dir = Path('project-scipt/runtime/test-download-ceval-run') / str(uuid4())
        output_dir.mkdir(parents=True, exist_ok=True)
        buffer = io.StringIO()

        with patch(
            'backend.tools.download_ceval.SUBJECTS',
            {
                'high_school_mathematics': '高中数学',
                'high_school_physics': '高中物理',
            },
        ):
            with patch(
                'backend.tools.download_ceval.download_subject_dataset',
                side_effect=[12, RuntimeError('boom')],
            ):
                completed = run(output_dir=output_dir, stdout=buffer)

        self.assertEqual(1, completed)
        self.assertIn('high_school_mathematics', buffer.getvalue())
        self.assertIn('警告', buffer.getvalue())


if __name__ == '__main__':
    unittest.main()
