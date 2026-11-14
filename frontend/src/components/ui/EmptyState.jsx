export default function EmptyState({ title = 'No data yet', hint, icon = 'ring', compact = false }) {
  return (
    <div className={`empty ${compact ? 'empty-compact' : ''}`}>
      <svg width="28" height="28" viewBox="0 0 28 28" fill="none" aria-hidden="true">
        {icon === 'ring' ? (
          <>
            <circle cx="14" cy="14" r="11" stroke="currentColor" strokeWidth="1.2" strokeDasharray="3 4" />
            <circle cx="14" cy="14" r="2.5" fill="currentColor" />
          </>
        ) : (
          <path d="M14 4 26 24H2L14 4Z M14 12v6 M14 21v.1" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
        )}
      </svg>
      <strong>{title}</strong>
      {hint && <span>{hint}</span>}
    </div>
  )
}
