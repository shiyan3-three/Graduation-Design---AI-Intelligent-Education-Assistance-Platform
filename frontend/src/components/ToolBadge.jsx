import { getToolLabel } from '../tool-labels.js';

export function ToolBadge({ tool }) {
  const status = tool?.status === 'error' ? 'error' : 'success';
  const label = getToolLabel(tool?.tool_name ?? '');

  return (
    <span className={`tool-badge is-${status}`}>
      <span className="tool-badge__dot" aria-hidden="true" />
      <span className="tool-badge__label">{label}</span>
      <span className="tool-badge__status">{status === 'error' ? '失败' : '成功'}</span>
    </span>
  );
}
