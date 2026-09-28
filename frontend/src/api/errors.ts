import type { components } from './schema';

export type ErrorBody = components['schemas']['ErrorResponse'];

/** Thrown for any non-2xx API response; carries the server's envelope. */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string | null;
  readonly errors: string[];

  constructor(status: number, body: Partial<ErrorBody> | undefined) {
    super(typeof body?.detail === 'string' ? body.detail : 'Щось пішло не так. Спробуйте ще раз.');
    this.status = status;
    this.code = body?.code ?? null;
    this.errors = Array.isArray(body?.errors) ? body.errors : [];
  }
}

type FetchResult<T> = { data?: T; error?: unknown; response: Response };

/**
 * Turn an openapi-fetch result into a value or a thrown ApiError, which is
 * the shape TanStack Query's queryFn/mutationFn want.
 */
export async function unwrap<T>(promise: Promise<FetchResult<T>>): Promise<T> {
  const { data, error, response } = await promise;
  if (error !== undefined || !response.ok) {
    throw new ApiError(response.status, (error ?? undefined) as Partial<ErrorBody> | undefined);
  }
  return data as T;
}

export function errorMessage(err: unknown): string {
  if (err instanceof ApiError) return err.message;
  if (err instanceof Error) return 'Немає зʼєднання з сервером. Спробуйте ще раз.';
  return 'Щось пішло не так.';
}
