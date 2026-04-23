from __future__ import annotations

import csv
import json
import os
import unittest
from pathlib import Path
from shutil import rmtree
from typing import Optional
from uuid import uuid4
from unittest.mock import patch

from backend import database
from backend.tools.import_ceval import import_ceval_directory
from backend.tools.question_tool import question_tool


class QuestionToolTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp_dir = Path('project-scipt/runtime/test-question-tool') / str(uuid4())
        self._temp_dir.mkdir(parents=True, exist_ok=True)
        self._data_dir = self._temp_dir / 'ceval_data'
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._original_db_path = database.DB_PATH
        self._original_mock_mode = os.environ.get('LLM_MOCK_MODE')
        self._original_api_key = os.environ.get('LLM_API_KEY')
        self._original_model = os.environ.get('LLM_MODEL')
        database.DB_PATH = self._temp_dir / 'question_tool.db'
        database.init_database()

    def tearDown(self) -> None:
        database.DB_PATH = self._original_db_path
        self._restore_env('LLM_MOCK_MODE', self._original_mock_mode)
        self._restore_env('LLM_API_KEY', self._original_api_key)
        self._restore_env('LLM_MODEL', self._original_model)
        rmtree(self._temp_dir, ignore_errors=True)

    def test_import_ceval_directory_loads_rows_into_question_bank(self) -> None:
        self._write_csv(
            self._data_dir / 'high_school_mathematics.csv',
            [
                {
                    'id': '1',
                    'question': '在直角三角形中，勾股定理描述的是哪一组关系？',
                    'A': '斜边和等于直角边和',
                    'B': '两直角边平方和等于斜边平方',
                    'C': '周长相等',
                    'D': '面积相等',
                    'answer': 'B',
                    'explanation': '勾股定理说明两直角边平方和等于斜边平方。',
                }
            ],
        )

        imported = import_ceval_directory(self._data_dir)

        self.assertEqual(1, imported)
        connection = database.get_connection()
        try:
            row = connection.execute(
                'SELECT subject, topic, answer, source FROM question_bank'
            ).fetchone()
        finally:
            connection.close()

        self.assertEqual('high_school_mathematics', row['subject'])
        self.assertEqual('勾股定理', row['topic'])
        self.assertEqual('B', row['answer'])
        self.assertEqual('ceval', row['source'])

    def test_question_tool_returns_local_question_when_topic_matches(self) -> None:
        self._seed_question_bank()

        payload = json.loads(question_tool('勾股定理'))

        self.assertIn('勾股定理', payload['question'])
        self.assertEqual('B', payload['answer'])
        self.assertEqual('ceval', payload['source'])
        self.assertEqual('两直角边平方和等于斜边平方', payload['options']['B'])

    def test_question_tool_returns_mock_generated_question_when_local_bank_misses(self) -> None:
        os.environ['LLM_MOCK_MODE'] = '1'
        os.environ.pop('LLM_API_KEY', None)
        os.environ.pop('LLM_MODEL', None)

        payload = json.loads(question_tool('热力学第一定律'))

        self.assertEqual('llm_generated', payload['source'])
        self.assertIn('question', payload)
        self.assertEqual({'A', 'B', 'C', 'D'}, set(payload['options'].keys()))

    def test_question_tool_returns_error_text_when_generation_fails(self) -> None:
        with patch('backend.tools.question_tool.generate_question_with_llm', side_effect=RuntimeError('boom')):
            result = question_tool('一个本地题库中不存在的知识点')

        self.assertIn('出题错误', result)

    def _seed_question_bank(self) -> None:
        self._write_csv(
            self._data_dir / 'high_school_mathematics.csv',
            [
                {
                    'id': '1',
                    'question': '在直角三角形中，勾股定理描述的是哪一组关系？',
                    'A': '斜边和等于直角边和',
                    'B': '两直角边平方和等于斜边平方',
                    'C': '周长相等',
                    'D': '面积相等',
                    'answer': 'B',
                    'explanation': '勾股定理说明两直角边平方和等于斜边平方。',
                }
            ],
        )
        import_ceval_directory(self._data_dir)

    def _write_csv(self, path: Path, rows: list[dict[str, str]]) -> None:
        with path.open('w', encoding='utf-8-sig', newline='') as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=['id', 'question', 'A', 'B', 'C', 'D', 'answer', 'explanation'],
            )
            writer.writeheader()
            writer.writerows(rows)

    def _restore_env(self, key: str, value: Optional[str]) -> None:
        if value is None:
            os.environ.pop(key, None)
            return

        os.environ[key] = value


if __name__ == '__main__':
    unittest.main()
