export function InputBar({
  value,
  onChange,
  onSubmit,
  onKeyDown,
  disabled,
}) {
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
        className="input-bar__field"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        onKeyDown={onKeyDown}
        placeholder="输入你想复习的问题，按 Enter 发送，Shift + Enter 换行"
        rows={2}
      />
      <button type="submit" className="input-bar__submit" disabled={disabled || !value.trim()}>
        {disabled ? '发送中…' : '发送'}
      </button>
    </form>
  );
}
