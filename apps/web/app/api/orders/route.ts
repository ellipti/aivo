export async function GET() {
  const url = `${process.env['NEXT_PUBLIC_API_EXECUTOR_URL']}/orders`;
  const res = await fetch(url, { cache: 'no-store' });
  const json = await res.json();
  return Response.json(json);
}
