import { z } from 'zod';

export const OrderSchema = z.object({
  instrument: z.string(),
  units: z.number(),
  side: z.enum(['buy', 'sell']),
});

export type Order = z.infer<typeof OrderSchema>;

export const constants = {
  locales: ['en', 'mn'] as const,
};

