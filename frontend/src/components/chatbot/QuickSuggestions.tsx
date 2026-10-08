interface Props { suggestions: string[]; onSelect: (text: string) => void; variant?: 'list' | 'chips' }

export function QuickSuggestions({ suggestions, onSelect, variant = 'list' }: Props) {
  return (
    <ul className={`cb-suggestions cb-suggestions--${variant}`} aria-label="Suggested questions">
      {suggestions.map((s) => (
        <li key={s}><button type="button" className="cb-suggestion" onClick={() => onSelect(s)}>{s}</button></li>
      ))}
    </ul>
  );
}
