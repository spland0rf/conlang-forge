import React from "react";
import { Card, H2, Muted } from "../ui/components";
import type { LanguageSummary } from "../types";

// The settings editor arrives in the next update of the app.
export default function SettingsTab(_: { onOpenLanguage(l: LanguageSummary): void }) {
  return (
    <Card>
      <H2>Settings</H2>
      <Muted>The settings editor is coming to the app very soon. For now, change settings on the website; they apply to this app too.</Muted>
    </Card>
  );
}
