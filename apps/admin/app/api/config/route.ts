import { readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';

const configPath = path.resolve(process.cwd(), '../../packages/shared/config.json');

export async function GET() {
  try {
    const raw = await readFile(configPath, 'utf-8');
    const json = JSON.parse(raw);
    return Response.json(json);
  } catch (e: any) {
    return Response.json({ error: e?.message || 'read_error' }, { status: 500 });
  }
}

export async function PUT(request: Request) {
  try {
    const body = await request.json();
    await writeFile(configPath, JSON.stringify(body, null, 2), 'utf-8');
    return Response.json({ ok: true });
  } catch (e: any) {
    return Response.json({ error: e?.message || 'write_error' }, { status: 500 });
  }
}
