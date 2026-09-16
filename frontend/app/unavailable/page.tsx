"use client";

import { useRouter } from "next/navigation";
import { ServerErrorView } from "@/components/common/ServerErrorView";

/** Standalone preview of the global error state (the search page shows it on real API failures). */
export default function UnavailablePage() {
  const router = useRouter();
  return (
    <main>
      <ServerErrorView
        code="ERR_NETWORK · 503 · verification-service"
        onRetry={() => router.refresh()}
        onBack={() => router.push("/")}
      />
    </main>
  );
}
