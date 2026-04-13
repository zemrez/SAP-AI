import { Suspense } from 'react';
import AnomalyDetailClient from './AnomalyDetailClient';

export default function AnomalyDetailPage() {
  return (
    <Suspense fallback={<div className="p-8 text-center text-sm text-slate-500">Loading...</div>}>
      <AnomalyDetailClient />
    </Suspense>
  );
}
