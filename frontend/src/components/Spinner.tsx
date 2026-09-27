/** Centered loading indicator for page-level queries. */
export function PageLoader() {
  return (
    <div className="page-loader" role="progressbar" aria-label="Завантаження">
      <div className="page-loader__spinner" />
    </div>
  );
}

export function PageError({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="page-error">
      <p>{message}</p>
      {onRetry && (
        <button type="button" className="page-error__retry" onClick={onRetry}>
          Спробувати ще раз
        </button>
      )}
    </div>
  );
}
