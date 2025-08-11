'use client';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';

const Schema = z.object({ email: z.string().email() });
type Values = z.infer<typeof Schema>;

export default function ForgotPage() {
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<Values>({ resolver: zodResolver(Schema) });
  const onSubmit = async (_data: Values) => {
    alert('Password reset link sent (mock).');
  };
  return (
    <main className="container mx-auto px-4 py-12 max-w-md">
      <h1 className="text-2xl font-semibold mb-6">Forgot password</h1>
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <div>
          <label className="block text-sm mb-1">Email</label>
          <input
            className="w-full border rounded-md px-3 py-2"
            type="email"
            {...register('email')}
          />
          {errors.email && <p className="text-sm text-red-500">{errors.email.message}</p>}
        </div>
        <button
          disabled={isSubmitting}
          className="w-full rounded-md bg-primary text-primary-foreground py-2"
        >
          Send reset link
        </button>
      </form>
    </main>
  );
}
