import test from 'node:test';
import assert from 'node:assert/strict';

import { createMessageElement } from '../src/message-element.js';

class FakeElement {
  constructor(tagName) {
    this.tagName = tagName.toUpperCase();
    this.className = '';
    this.children = [];
    this._textContent = '';
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

  findAllByClassName(className) {
    const matches = [];
    if (this.className.split(/\s+/).includes(className)) {
      matches.push(this);
    }

    for (const child of this.children) {
      if (!(child instanceof FakeElement)) {
        continue;
      }

      matches.push(...child.findAllByClassName(className));
    }

    return matches;
  }
}

global.document = {
  createElement(tagName) {
    return new FakeElement(tagName);
  },
};

test('createMessageElement renders tool tags for assistant tool calls', () => {
  const element = createMessageElement({
    role: 'assistant',
    label: 'AI',
    content: '这里是回答',
    pending: false,
    failed: false,
    toolsUsed: [
      { label: '知识查询', status: 'success' },
      { label: '计算器', status: 'error' },
    ],
  });

  const toolTags = element.findByClassName('tool-tags');
  const tags = element.findAllByClassName('tool-tag');

  assert.ok(toolTags);
  assert.equal(tags.length, 2);
  assert.match(tags[0].textContent, /知识查询/);
  assert.match(tags[0].textContent, /成功/);
  assert.match(tags[1].textContent, /计算器/);
  assert.match(tags[1].textContent, /失败/);
  assert.ok(tags[0].className.includes('is-success'));
  assert.ok(tags[1].className.includes('is-error'));
});

test('createMessageElement omits tool tags when a message has no tool usage', () => {
  const element = createMessageElement({
    role: 'assistant',
    label: 'AI',
    content: '普通回复',
    pending: false,
    failed: false,
    toolsUsed: null,
  });

  assert.equal(element.findByClassName('tool-tags'), null);
});
