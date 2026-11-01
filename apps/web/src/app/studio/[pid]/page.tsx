import StudioShell from '@/components/StudioShell';

export default function StudioPage({ params }: { params: { pid: string } }) {
  return <StudioShell pid={params.pid} />;
}
