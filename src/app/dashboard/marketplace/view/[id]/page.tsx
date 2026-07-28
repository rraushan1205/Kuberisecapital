import { StrategyFileViewer } from '@/features/dashboard/components/strategy-file-viewer';

export default async function StrategyViewPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <StrategyFileViewer strategyId={id} />;
}