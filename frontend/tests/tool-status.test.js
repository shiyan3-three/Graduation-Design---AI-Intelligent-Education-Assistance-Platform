import test from 'node:test';
import assert from 'node:assert/strict';

import {
  createInitialState,
  finishSessionDetailLoad,
} from '../src/chat-state.js';
import { getViewModel } from '../src/chat-view.js';

test('finishSessionDetailLoad preserves tool metadata for historical assistant messages', () => {
  const nextState = finishSessionDetailLoad(
    {
      ...createInitialState(),
      currentSessionId: 7,
      isLoadingSessionDetail: true,
    },
    {
      session: { id: 7 },
      messages: [
        {
          id: 301,
          role: 'assistant',
          content: '这是带工具的历史消息',
          tools_used: [
            {
              tool_name: 'calculator_tool',
              status: 'success',
            },
          ],
        },
      ],
    }
  );

  assert.deepEqual(nextState.messages[0].toolsUsed, [
    {
      tool_name: 'calculator_tool',
      status: 'success',
    },
  ]);
});

test('getViewModel maps known tools into display labels', () => {
  const viewModel = getViewModel({
    ...createInitialState(),
    messages: [
      {
        id: 'assistant-history-1',
        role: 'assistant',
        content: '工具调用完成',
        pending: false,
        failed: false,
        toolsUsed: [
          { tool_name: 'calculator_tool', status: 'success' },
          { tool_name: 'knowledge_tool', status: 'error' },
          { tool_name: 'question_tool', status: 'success' },
          { tool_name: 'custom_tool', status: 'success' },
        ],
      },
    ],
  });

  assert.deepEqual(viewModel.messages[0].toolsUsed, [
    { label: '计算器', status: 'success' },
    { label: '知识查询', status: 'error' },
    { label: '出题', status: 'success' },
    { label: 'custom_tool', status: 'success' },
  ]);
});
