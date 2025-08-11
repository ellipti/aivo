export async function GET() {
  try {
    const url = `${process.env['ADMIN_EXECUTOR_URL']}/orders`;
    const res = await fetch(url, { cache: 'no-store' });
    const data = await res.json().catch(() => ({ error: true }));
    return new Response(JSON.stringify(data), {
      status: res.status,
      headers: { 'Content-Type': 'application/json' },
    });
  } catch (e: any) {
    return new Response(JSON.stringify({ error: true, message: String(e?.message || e) }), {
      status: 500,
    });
  }
}
