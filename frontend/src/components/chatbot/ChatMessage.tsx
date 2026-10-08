import { GraduationCap } from 'lucide-react';
import type { ChatMessage as Message } from '../../types/chatbot';
import { formatTime } from '../../utils/chatbotUtils';
import { RecommendationBlockView } from './RecommendationCards';
import { RichText } from './RichText';

export function AssistantAvatar() {
  return <span className="cb-avatar" aria-hidden="true"><GraduationCap size={16} /></span>;
}

export function ChatMessage({ message }: { message: Message }) {
  const isUser = message.role === 'user';
  return (
    <div className={`cb-msg ${isUser ? 'cb-msg--user' : 'cb-msg--ai'}`} data-status={message.status}>
      {!isUser && <AssistantAvatar />}
      <div className="cb-msg__body">
        <span className="cb-sr">{isUser ? 'You said:' : 'Assistant said:'}</span>
        {message.content && <div className="cb-bubble">{isUser ? <p>{message.content}</p> : <RichText text={message.content} />}</div>}
        {message.blocks?.map((b, i) => <RecommendationBlockView key={i} block={b} />)}
        <time className="cb-msg__time" dateTime={message.createdAt}>{formatTime(message.createdAt)}</time>
      </div>
    </div>
  );
}
