'use client';
import { useState } from 'react';

type User = { id: string; email: string; role: 'user' | 'admin' };

const initial: User[] = [
  { id: '1', email: 'admin@aivo.ai', role: 'admin' },
  { id: '2', email: 'user@aivo.ai', role: 'user' },
];

export default function UsersPage() {
  const [users, setUsers] = useState<User[]>(initial);

  const toggleRole = (id: string) => {
    setUsers((u) =>
      u.map((x) => (x.id === id ? { ...x, role: x.role === 'admin' ? 'user' : 'admin' } : x)),
    );
  };

  const addUser = () => {
    const id = String(Date.now());
    setUsers((u) => [...u, { id, email: `user${id}@aivo.ai`, role: 'user' }]);
  };

  const remove = (id: string) => setUsers((u) => u.filter((x) => x.id !== id));

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-semibold">Users</h1>
        <button onClick={addUser} className="border rounded-md px-3 py-2">
          Add
        </button>
      </div>
      <div className="rounded-lg border overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-muted/50 text-left">
              <th className="p-2">Email</th>
              <th className="p-2">Role</th>
              <th className="p-2">Actions</th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id} className="border-t">
                <td className="p-2">{u.email}</td>
                <td className="p-2">{u.role}</td>
                <td className="p-2 space-x-2">
                  <button onClick={() => toggleRole(u.id)} className="border rounded-md px-2 py-1">
                    Toggle Role
                  </button>
                  <button onClick={() => remove(u.id)} className="border rounded-md px-2 py-1">
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
