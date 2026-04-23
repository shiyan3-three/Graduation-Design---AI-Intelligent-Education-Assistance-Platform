from __future__ import annotations

import json
import sqlite3
import unittest
from unittest.mock import patch

from backend.tools.question_tool import question_tool


class QuestionToolLocalMatchV2Tests(unittest.TestCase):
    def test_question_tool_prefers_local_bank_for_alias_topic(self) -> None:
        connection = sqlite3.connect(':memory:')
        connection.row_factory = sqlite3.Row
        connection.execute(
            """
            CREATE TABLE question_bank (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject TEXT NOT NULL,
                topic TEXT NOT NULL,
                question TEXT NOT NULL,
                option_a TEXT,
                option_b TEXT,
                option_c TEXT,
                option_d TEXT,
                answer TEXT NOT NULL,
                explanation TEXT DEFAULT '',
                source TEXT NOT NULL DEFAULT 'ceval'
            )
            """
        )
        connection.execute(
            """
            INSERT INTO question_bank (
                subject, topic, question, option_a, option_b, option_c, option_d,
                answer, explanation, source
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                'high_school_mathematics',
                'high_school_mathematics',
                '已知抛物线 y = x^2 - 4x + 3 与 x 轴交于两点，则其顶点坐标是____',
                '(2, -1)',
                '(2, 1)',
                '(1, -2)',
                '(1, 2)',
                'A',
                '这是典型的二次函数图像问题，可由配方法求顶点。',
                'ceval',
            ),
        )
        connection.commit()

        with patch('backend.tools.question_tool_impl.database.get_connection', return_value=connection):
            payload = json.loads(question_tool('二次函数'))

        self.assertEqual('ceval', payload['source'])
        self.assertIn('抛物线', payload['question'])
        self.assertEqual('A', payload['answer'])


if __name__ == '__main__':
    unittest.main()
