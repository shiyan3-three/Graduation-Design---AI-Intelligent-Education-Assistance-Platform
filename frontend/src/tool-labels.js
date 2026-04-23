export const TOOL_LABELS = {
  calculator_tool: '计算器',
  knowledge_tool: '知识查询',
  question_tool: '出题',
};

export function getToolLabel(toolName) {
  return TOOL_LABELS[toolName] ?? toolName;
}
