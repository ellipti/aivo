'use client';
import { useEffect, useState } from 'react';

export default function useEventStream(url: string) {
  const [events, setEvents] = useState<any[]>([]);
  useEffect(() => {
    const es = new EventSource(url);
    es.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        setEvents((prev) => [data, ...prev].slice(0, 200));
      } catch {
        // ignore
      }
    };
    es.onerror = () => {
      // auto-retry via browser
    };
    return () => es.close();
  }, [url]);
  return events;
}
