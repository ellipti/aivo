'use client';
import { useRouter } from 'next/navigation';

export default function AdminLoginPage() {
  const router = useRouter();
  return (
    <main className="container mx-auto px-4 py-12 max-w-md">
      <h1 className="text-2xl font-semibold mb-6">Admin Login</h1>
      <button
        className="w-full rounded-md bg-primary text-primary-foreground py-2"
        onClick={() => {
          document.cookie = `role=admin; path=/`;
          router.push('/dashboard');
        }}
      >
        Continue as Admin (mock)
      </button>
    </main>
  );
}
