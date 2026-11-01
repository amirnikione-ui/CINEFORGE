import StudioClient from "@/components/StudioClient";

export const metadata = {
  title: "Studio · CINEFORGE",
};

export default async function StudioPage({ params }: { params: { projectId: string } }) {
  const { projectId } = await params;
  return <StudioClient projectId={projectId} />;
}
