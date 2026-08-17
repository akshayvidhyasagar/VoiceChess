import { useState } from "react";

export interface GameSetupConfig {
  input_mode: "ptt" | "voice";
  game_mode: "single" | "double";
  elo?: number;
  human_color: "white" | "black" | "random";
}

export function useSetupWizard() {
  const [isSetupComplete, setIsSetupComplete] = useState(false);
  const [setupConfig, setSetupConfig] = useState<GameSetupConfig | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submitSetup = async (config: GameSetupConfig) => {
    setIsSubmitting(true);
    setError(null);

    try {
      const response = await fetch("/api/setup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(config),
      });

      if (!response.ok) throw new Error("Setup failed");

      setSetupConfig(config);
      setIsSetupComplete(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setIsSubmitting(false);
    }
  };

  const resetSetup = async () => {
    setIsSubmitting(true);
    try {
      const response = await fetch("/api/play-again", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ play_again: "yes" }),
      });

      if (!response.ok) throw new Error("Reset failed");

      setIsSetupComplete(false);
      setSetupConfig(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setIsSubmitting(false);
    }
  };

  return {
    isSetupComplete,
    setupConfig,
    isSubmitting,
    error,
    submitSetup,
    resetSetup,
  };
}
