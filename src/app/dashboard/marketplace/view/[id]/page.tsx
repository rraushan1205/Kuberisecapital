import { StrategyFileViewer } from '@/features/dashboard/components/strategy-file-viewer';

export default function StrategyViewPage({
  params,
}: {
  params: { id: string };
}) {
  return <StrategyFileViewer strategyId={params.id} />;
}
