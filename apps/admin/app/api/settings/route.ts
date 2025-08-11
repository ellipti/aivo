import { store } from '../../../lib/store';
import { SettingsSchema } from '../../../src/types';

export async function GET() {
  return Response.json(store.settings);
}

export async function PUT(request: Request) {
  const body = await request.json();
  const parsed = SettingsSchema.safeParse(body);
  if (!parsed.success) return Response.json({ error: 'invalid' }, { status: 400 });
  store.setSettings(parsed.data);
  return Response.json({ ok: true });
}
