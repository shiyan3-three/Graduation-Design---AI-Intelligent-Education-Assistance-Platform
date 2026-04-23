import { useRef, useEffect } from 'react';

export function InputBar({
  value,
  onChange,
  onSubmit,
  onKeyDown,
  disabled,
}) {
  const textareaRef = useRef(null);

  // 这里的依赖数组包括 value，当外部清空输入框时，高度可以还原
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'; // 先重置以便获取真实 scrollHeight
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  }, [value]);

  return (
    <form
      className="input-bar"
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit();
      }}
    >
      <label className="sr-only" htmlFor="chat-input">
        输入消息
      </label>
      <textarea
        id="chat-input"
        ref={textareaRef}
        className="input-bar__field"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        onKeyDown={onKeyDown}
        placeholder="输入你想复习的问题，按 Enter 发送，Shift + Enter 换行"
        rows={1}
        disabled={disabled}
      />
      <button type="submit" className="input-bar__submit" disabled={disabled || !value.trim()}>
        {disabled ? '发送中…' : '发送'}
      </button>
    </form>
  );
}
