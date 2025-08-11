'use client';
import { useState } from 'react';
import { ComposableMap, Geographies, Geography, Marker, Annotation } from 'react-simple-maps';
import { motion } from 'framer-motion';
import worldData from 'world-atlas/countries-110m.json';

const markers = [
  { name: 'London', coordinates: [-0.1276, 51.5074] },
  { name: 'New York', coordinates: [-74.006, 40.7128] },
  { name: 'Tokyo', coordinates: [139.6917, 35.6895] },
  { name: 'Sydney', coordinates: [151.2093, -33.8688] },
];

export function WorldMapHero() {
  const [hoverId, setHoverId] = useState<string | null>(null);

  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
      <div className="w-full max-w-3xl mx-auto">
        <ComposableMap projectionConfig={{ scale: 140 }}>
          <Geographies geography={worldData as any}>
            {(params: any) =>
              (params?.geographies as any[]).map((geo: any) => (
                <Geography
                  key={geo.rsmKey}
                  geography={geo}
                  onMouseEnter={() => setHoverId(geo.rsmKey)}
                  onMouseLeave={() => setHoverId((id) => (id === geo.rsmKey ? null : id))}
                  style={{
                    default: { fill: '#e5e7eb', outline: 'none' },
                    hover: { fill: '#a3a3a3', outline: 'none' },
                  }}
                  fill={hoverId === geo.rsmKey ? '#a3a3a3' : '#e5e7eb'}
                />
              ))
            }
          </Geographies>

          {markers.map((m) => (
            <Marker key={m.name} coordinates={m.coordinates as any}>
              <g className="relative">
                <circle r={3} fill="#ef4444" />
                <circle r={8} className="animate-ping" fill="#ef4444" opacity={0.35} />
              </g>
            </Marker>
          ))}

          <Annotation
            subject={[-0.1276, 51.5074] as any}
            dx={10}
            dy={-10}
            connectorProps={{ stroke: '#4f46e5', strokeWidth: 1, strokeLinecap: 'round' }}
          >
            <text x={4} y={-4} className="text-xs fill-current" style={{ fontSize: '10px' }}>
              London
            </text>
          </Annotation>
        </ComposableMap>
      </div>
    </motion.div>
  );
}
