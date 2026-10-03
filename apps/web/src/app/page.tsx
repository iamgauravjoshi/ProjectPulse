import { Suspense } from "react";
import { WorkspaceSkeleton } from "../components/workspace/feedback";
import { WorkspaceScreen } from "../features/workspace/workspace-screen";

export default function WorkspacePage() {
  return (
    <Suspense fallback={<WorkspaceSkeleton />}>
      <WorkspaceScreen />
    </Suspense>
  );
}
