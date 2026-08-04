export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(path, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
  });

  if (!resp.ok) {
    const text = await resp.text().catch(() => "");
    throw new ApiError(text || resp.statusText, resp.status);
  }

  return (await resp.json()) as T;
}

