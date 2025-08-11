import { store, InMemoryUser } from '../../../../lib/store';

export async function PUT(_: Request, { params }: { params: { id: string } }) {
  const id = params.id;
  const body = (await _.json()) as Partial<InMemoryUser>;
  const next = store.users.map((u) => (u.id === id ? { ...u, ...body, id } : u));
  store.setUsers(next);
  const updated = next.find((u) => u.id === id);
  return Response.json(updated);
}
