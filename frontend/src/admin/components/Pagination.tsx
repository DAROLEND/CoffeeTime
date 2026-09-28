/** The admin "page-btn" pager: ‹ 1 2 [3] 4 5 › around the current page. */
export function Pagination({ page, totalPages, onPage }: { page: number; totalPages: number; onPage: (page: number) => void }) {
  if (totalPages <= 1) return null;
  const from = Math.max(1, page - 2);
  const to = Math.min(totalPages, page + 2);
  const pages = Array.from({ length: to - from + 1 }, (_, i) => from + i);
  return (
    <div className="pagination">
      {page > 1 && (
        <button type="button" className="page-btn" onClick={() => onPage(page - 1)} aria-label="Попередня сторінка">
          ‹
        </button>
      )}
      {pages.map((i) => (
        <button key={i} type="button" className={`page-btn${i === page ? ' active' : ''}`} onClick={() => onPage(i)} aria-current={i === page ? 'page' : undefined}>
          {i}
        </button>
      ))}
      {page < totalPages && (
        <button type="button" className="page-btn" onClick={() => onPage(page + 1)} aria-label="Наступна сторінка">
          ›
        </button>
      )}
    </div>
  );
}
