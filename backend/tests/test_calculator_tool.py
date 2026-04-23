from __future__ import annotations

import unittest

from backend.tools.calculator_tool import calculator_tool


class CalculatorToolTests(unittest.TestCase):
    def test_calculator_tool_returns_result_for_valid_expression(self) -> None:
        self.assertEqual('1024', calculator_tool('2^10'))

    def test_calculator_tool_returns_error_text_for_invalid_expression(self) -> None:
        result = calculator_tool('2 + )')

        self.assertIsInstance(result, str)
        self.assertIn('错误', result)


if __name__ == '__main__':
    unittest.main()
