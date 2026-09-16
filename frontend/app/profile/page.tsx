import { Suspense } from "react";
import { ProfileScreen } from "@/components/profile/ProfileScreen";

export default function ProfilePage() {
  return (
    <main>
      <Suspense>
        <ProfileScreen />
      </Suspense>
    </main>
  );
}
