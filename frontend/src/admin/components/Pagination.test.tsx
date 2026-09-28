import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it, vi } from 'vitest';
import { Pagination } from './Pagination';

it('renders nothing for a single page', () => {
  const { container } = render(<Pagination page={1} totalPages={1} onPage={() => {}} />);
  expect(container).toBeEmptyDOMElement();
});

it('shows a window of two pages around the current one', async () => {
  const onPage = vi.fn();
  render(<Pagination page={5} totalPages={9} onPage={onPage} />);
  expect(screen.getAllByRole('button').map((b) => b.textContent)).toEqual(['‹', '3', '4', '5', '6', '7', '›']);
  expect(screen.getByRole('button', { name: '5' })).toHaveAttribute('aria-current', 'page');
  await userEvent.click(screen.getByLabelText('Наступна сторінка'));
  expect(onPage).toHaveBeenCalledWith(6);
});
