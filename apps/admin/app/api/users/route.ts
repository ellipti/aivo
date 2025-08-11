import { store, InMemoryUser } from '../../../lib/store';

export async function GET() {
  return Response.json({ items: store.users });
}

export async function POST(request: Request) {
  const body = (await request.json()) as Partial<InMemoryUser>;
  const id = String(Date.now());
  const user: InMemoryUser = {
    id,
    username: body.username || `user_${id}`,
    role: body.role || 'user',
    status: body.status || 'active',
    createdAt: new Date().toISOString(),
  };
  store.setUsers([...store.users, user]);
  return Response.json(user, { status: 201 });
}
