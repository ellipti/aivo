export async function GET() {
  const analyzerUrl = process.env['NEXT_PUBLIC_API_ANALYZER_URL'] || 'http://localhost:7001';
  const executorUrl = process.env['ADMIN_EXECUTOR_URL'] || 'http://localhost:7002';

  async function ping(url: string) {
    const start = Date.now();
    try {
      const r = await fetch(`${url}/health`, { cache: 'no-store' });
      const ms = Date.now() - start;
      if (!r.ok) return { status: 'down', ms } as const;
      return { status: 'ok', ms } as const;
    } catch {
      const ms = Date.now() - start;
      return { status: 'down', ms } as const;
    }
  }

  const [analyzer, executor] = await Promise.all([ping(analyzerUrl), ping(executorUrl)]);
  return Response.json({ analyzer, executor });
}
