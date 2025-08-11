export async function POST(request: Request) {
  const body = await request.json();
  const url = `${process.env['NEXT_PUBLIC_API_EXECUTOR_URL']}/orders/place`;
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const json = await res.json();
  return Response.json(json);
}
