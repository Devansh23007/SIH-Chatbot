import { AlertCircle, RefreshCw } from 'lucide-react';
import { chatbotConfig } from '../../config/chatbotConfig';
import type { ChatErrorCode } from '../../types/chatbot';

/** Shows friendly copy only; raw backend errors never reach the UI. */
export function ChatErrorState({ code, onRetry }: { code: ChatErrorCode; onRetry?: () => void }) {
  return (
    <div className="cb-error" role="alert">
      <AlertCircle size={16} aria-hidden="true" />
      <p>{chatbotConfig.errorMessages[code]}</p>
      {onRetry && code !== 'auth' && (
        <button type="button" className="cb-btn cb-btn--ghost" onClick={onRetry}>
          <RefreshCw size={14} aria-hidden="true" /> Retry
        </button>
      )}
    </div>
  );
}
