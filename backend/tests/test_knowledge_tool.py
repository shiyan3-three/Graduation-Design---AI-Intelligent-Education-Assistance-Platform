from __future__ import annotations

import unittest
from unittest.mock import Mock, patch


class KnowledgeToolTests(unittest.TestCase):
    def test_knowledge_tool_returns_generated_summary_with_source_lines(self) -> None:
        from backend.tools.knowledge_tool import knowledge_tool

        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            'choices': [
                {
                    'message': {
                        'content': '勾股定理说明直角三角形两直角边平方和等于斜边平方。',
                        'role': 'assistant',
                    }
                }
            ],
            'references': [
                {
                    'title': '勾股定理 - 百度百科',
                    'content': '勾股定理揭示了直角三角形三边长度关系。',
                    'url': 'https://baike.baidu.com/item/勾股定理',
                    'website': '百度百科',
                },
                {
                    'title': '勾股定理证明',
                    'content': '常见证明包括面积法、相似三角形法等。',
                    'url': 'https://example.com/pythagorean-proof',
                    'website': '示例站点',
                },
            ]
        }

        with patch.dict('os.environ', {'BAIDU_SEARCH_API_KEY': 'test-key'}, clear=False):
            with patch('backend.tools.knowledge_tool.requests.post', return_value=response) as mock_post:
                result = knowledge_tool('什么是勾股定理')

        self.assertIn('勾股定理说明直角三角形两直角边平方和等于斜边平方', result)
        self.assertIn('来源1：勾股定理 - 百度百科（百度百科）', result)
        self.assertIn('来源2：勾股定理证明（示例站点）', result)
        self.assertEqual(
            'https://qianfan.baidubce.com/v2/ai_search/chat/completions',
            mock_post.call_args.args[0],
        )
        self.assertEqual(
            '什么是勾股定理',
            mock_post.call_args.kwargs['json']['messages'][0]['content'],
        )
        self.assertEqual('baidu_search_v2', mock_post.call_args.kwargs['json']['search_source'])
        self.assertEqual('required', mock_post.call_args.kwargs['json']['search_mode'])
        self.assertFalse(mock_post.call_args.kwargs['json']['stream'])

    def test_knowledge_tool_falls_back_to_references_when_generated_summary_is_missing(self) -> None:
        from backend.tools.knowledge_tool import knowledge_tool

        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            'choices': [{'message': {'content': '', 'role': 'assistant'}}],
            'references': [
                {
                    'title': '勾股定理 - 百度百科',
                    'content': '勾股定理揭示了直角三角形三边长度关系。',
                    'url': 'https://baike.baidu.com/item/勾股定理',
                    'website': '百度百科',
                }
            ],
        }

        with patch.dict('os.environ', {'BAIDU_SEARCH_API_KEY': 'test-key'}, clear=False):
            with patch('backend.tools.knowledge_tool.requests.post', return_value=response):
                result = knowledge_tool('什么是勾股定理')

        self.assertIn('1. 勾股定理 - 百度百科', result)
        self.assertIn('勾股定理揭示了直角三角形三边长度关系', result)

    def test_knowledge_tool_returns_error_text_when_api_key_is_missing(self) -> None:
        from backend.tools.knowledge_tool import knowledge_tool

        with patch.dict('os.environ', {}, clear=True):
            result = knowledge_tool('什么是勾股定理')

        self.assertIn('知识查询错误', result)

    def test_knowledge_tool_returns_error_text_when_request_fails(self) -> None:
        from backend.tools.knowledge_tool import knowledge_tool

        with patch.dict('os.environ', {'BAIDU_SEARCH_API_KEY': 'test-key'}, clear=False):
            with patch(
                'backend.tools.knowledge_tool.requests.post',
                side_effect=RuntimeError('timeout'),
            ):
                result = knowledge_tool('什么是勾股定理')

        self.assertIn('知识查询错误', result)
        self.assertIn('timeout', result)


if __name__ == '__main__':
    unittest.main()
