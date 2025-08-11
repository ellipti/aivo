export async function POST(request: Request) {
  const body = await request.json();
  const url = `${process.env['WEB_EXECUTOR_URL']}/orders/place`;
  const idem = request.headers.get('Idempotency-Key') || undefined;
  const res = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(idem ? { 'Idempotency-Key': idem } : {}),
    },
    body: JSON.stringify(body),
    cache: 'no-store',
  });
  const data = await res.json().catch(() => ({}));
  return new Response(JSON.stringify(data), {
    status: res.status,
    headers: { 'Content-Type': 'application/json' },
  });
}
