import test from 'node:test';
import assert from 'node:assert/strict';

import {
  createInitialState,
  finishSubmission,
  startSubmission,
} from '../src/chat-state.js';
import { getViewModel } from '../src/chat-view.js';
import { createMessageElement } from '../src/message-element.js';

class FakeElement {
  constructor(tagName) {
    this.tagName = tagName.toUpperCase();
    this.className = '';
    this.children = [];
    this._textContent = '';
    this.dataset = {};
    this.type = '';
  }

  append(...children) {
    this.children.push(...children);
  }

  set textContent(value) {
    this._textContent = String(value);
    this.children = [];
  }

  get textContent() {
    if (this.children.length > 0) {
      return this.children
        .map((child) => (child instanceof FakeElement ? child.textContent : String(child)))
        .join('');
    }

    return this._textContent;
  }

  findByClassName(className) {
    if (this.className.split(/\s+/).includes(className)) {
      return this;
    }

    for (const child of this.children) {
      if (!(child instanceof FakeElement)) {
        continue;
      }

      const match = child.findByClassName(className);
      if (match) {
        return match;
      }
    }

    return null;
  }
}

global.document = {
  createElement(tagName) {
    return new FakeElement(tagName);
  },
};

test('startSubmission includes tool preference when resubmitting through a tool suggestion', () => {
  const state = {
    ...createInitialState(),
    currentSessionId: 9,
  };

  const result = startSubmission(
    state,
    '请解释勾股定理',
    { toolPreference: 'knowledge_tool' },
    () => 'local-tool-1'
  );

  assert.deepEqual(result.requestBody, {
    content: '请解释勾股定理',
    session_id: 9,
    tool_preference: 'knowledge_tool',
  });
});

test('finishSubmission preserves assistant tool suggestion metadata from the api response', () => {
  const state = {
    ...createInitialState(),
    isSending: true,
    messages: [{ id: 'local-6', role: 'user', content: '勾股定理', pending: true, failed: false }],
  };

  const nextState = finishSubmission(state, {
    session: { id: 21 },
    user_message: { id: 301, role: 'user', content: '勾股定理', tools_used: null },
    assistant_message: {
      id: 302,
      role: 'assistant',
      content: '这条消息更像是在问一个知识主题，如果你愿意我可以改用工具查询。',
      tools_used: [],
      tool_suggestion: {
        tool_name: 'knowledge_tool',
        recommended_prompt: '请解释勾股定理',
      },
    },
  });

  assert.deepEqual(nextState.messages[1].toolSuggestion, {
    tool_name: 'knowledge_tool',
    recommended_prompt: '请解释勾股定理',
  });
});

test('getViewModel maps tool suggestions into display metadata', () => {
  const viewModel = getViewModel({
    ...createInitialState(),
    messages: [
      {
        id: 'assistant-suggestion-1',
        role: 'assistant',
        content: '这条消息更像是在问一个知识主题，如果你愿意我可以改用工具查询。',
        pending: false,
        failed: false,
        toolsUsed: null,
        toolSuggestion: {
          tool_name: 'knowledge_tool',
          recommended_prompt: '请解释勾股定理',
        },
      },
    ],
  });

  assert.deepEqual(viewModel.messages[0].toolSuggestion, {
    toolName: 'knowledge_tool',
    label: '知识查询',
    recommendedPrompt: '请解释勾股定理',
  });
});

test('createMessageElement renders a tool suggestion action when provided', () => {
  const element = createMessageElement({
    id: 'assistant-suggestion-2',
    role: 'assistant',
    label: 'AI',
    content: '这条消息更像是在问一个知识主题，如果你愿意我可以改用工具查询。',
    pending: false,
    failed: false,
    toolsUsed: null,
    toolSuggestion: {
      toolName: 'knowledge_tool',
      label: '知识查询',
      recommendedPrompt: '请解释勾股定理',
    },
  });

  const suggestion = element.findByClassName('tool-suggestion');
  const action = element.findByClassName('tool-suggestion__button');

  assert.ok(suggestion);
  assert.ok(action);
  assert.match(suggestion.textContent, /知识查询/);
  assert.match(action.textContent, /使用工具/);
});
