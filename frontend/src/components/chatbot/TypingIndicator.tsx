import { AssistantAvatar } from './ChatMessage';

export function TypingIndicator() {
  return (
    <div className="cb-msg cb-msg--ai" role="status">
      <AssistantAvatar />
      <div className="cb-bubble cb-typing">
        <span className="cb-dot" /><span className="cb-dot" /><span className="cb-dot" />
        <span className="cb-sr">NCCT Career Assistant is thinking…</span>
      </div>
    </div>
  );
}
