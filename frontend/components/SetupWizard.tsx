"use client";

import React, { useState } from "react";

interface SetupWizardProps {
  onComplete: (config: SetupConfig) => void;
}

export interface SetupConfig {
  input_mode: "ptt" | "voice";
  game_mode: "single" | "double";
  elo?: number;
  human_color: "white" | "black" | "random";
}

export function SetupWizard({ onComplete }: SetupWizardProps) {
  const [step, setStep] = useState<1 | 2 | 3 | 4>(1);
  const [inputMode, setInputMode] = useState<"ptt" | "voice" | null>(null);
  const [gameMode, setGameMode] = useState<"single" | "double" | null>(null);
  const [elo, setElo] = useState(1600);
  const [humanColor, setHumanColor] = useState<"white" | "black" | "random">("random");

  const handleNext = () => {
    if (step === 1) {
      if (!inputMode) return;
      setStep(2);
    } else if (step === 2) {
      if (!gameMode) return;
      setStep(gameMode === "double" ? 4 : 3);
    } else if (step === 3) {
      setStep(4);
    }
  };

  const handleBack = () => {
    if (step === 4 && gameMode === "double") {
      setStep(2);
    } else {
      setStep((s) => (s === 1 ? 1 : (s - 1) as 1 | 2 | 3 | 4));
    }
  };

  const handleStartGame = () => {
    if (inputMode && gameMode && humanColor) {
      onComplete({
        input_mode: inputMode,
        game_mode: gameMode,
        elo: gameMode === "single" ? elo : undefined,
        human_color: humanColor,
      });
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center p-4 z-50">
      <div className="bg-zinc-800 rounded-lg shadow-xl p-8 max-w-md w-full">
        {/* Progress indicator */}
        <div className="mb-6">
          <div className="text-sm text-zinc-400 mb-2">
            Step {step} of 4
          </div>
          <div className="w-full bg-zinc-700 rounded-full h-2">
            <div
              className="bg-blue-500 h-2 rounded-full transition-all"
              style={{ width: `${(step / 4) * 100}%` }}
            />
          </div>
        </div>

        {/* Step 1: Input Mode Selection */}
        {step === 1 && (
          <div>
            <h2 className="text-xl font-bold text-white mb-4">
              Choose Input Mode
            </h2>
            <div className="space-y-3">
              <button
                onClick={() => setInputMode("ptt")}
                className={`w-full p-3 rounded border-2 text-left transition ${
                  inputMode === "ptt"
                    ? "border-blue-500 bg-blue-500 bg-opacity-10"
                    : "border-zinc-600 hover:border-zinc-500"
                }`}
              >
                <div className="font-semibold text-white">Push-to-Talk</div>
                <div className="text-sm text-zinc-300">Hold spacebar to record</div>
              </button>
              <button
                onClick={() => setInputMode("voice")}
                className={`w-full p-3 rounded border-2 text-left transition ${
                  inputMode === "voice"
                    ? "border-blue-500 bg-blue-500 bg-opacity-10"
                    : "border-zinc-600 hover:border-zinc-500"
                }`}
              >
                <div className="font-semibold text-white">Fully Voice</div>
                <div className="text-sm text-zinc-300">Hands-free, auto-detect</div>
              </button>
            </div>
          </div>
        )}

        {/* Step 2: Game Mode Selection */}
        {step === 2 && (
          <div>
            <h2 className="text-xl font-bold text-white mb-4">
              Choose Game Mode
            </h2>
            <div className="space-y-3">
              <button
                onClick={() => setGameMode("single")}
                className={`w-full p-3 rounded border-2 text-left transition ${
                  gameMode === "single"
                    ? "border-blue-500 bg-blue-500 bg-opacity-10"
                    : "border-zinc-600 hover:border-zinc-500"
                }`}
              >
                <div className="font-semibold text-white">Human vs Computer</div>
                <div className="text-sm text-zinc-300">Play against Stockfish</div>
              </button>
              <button
                onClick={() => setGameMode("double")}
                className={`w-full p-3 rounded border-2 text-left transition ${
                  gameMode === "double"
                    ? "border-blue-500 bg-blue-500 bg-opacity-10"
                    : "border-zinc-600 hover:border-zinc-500"
                }`}
              >
                <div className="font-semibold text-white">Human vs Human</div>
                <div className="text-sm text-zinc-300">Play with another person</div>
              </button>
            </div>
          </div>
        )}

        {/* Step 3: Match Customization (single mode only) */}
        {step === 3 && (
          <div>
            <h2 className="text-xl font-bold text-white mb-4">
              Customize Match
            </h2>

            {/* Difficulty Slider */}
            <div className="mb-6">
              <label className="text-sm text-zinc-300 mb-2 block">
                Difficulty: <span className="text-blue-400 font-semibold">{elo}</span>
              </label>
              <input
                type="range"
                min="800"
                max="3000"
                value={elo}
                onChange={(e) => setElo(Number(e.target.value))}
                className="w-full"
              />
              <div className="flex justify-between text-xs text-zinc-500 mt-1">
                <span>Beginner (800)</span>
                <span>Master (3000)</span>
              </div>
            </div>

            {/* Color Selection */}
            <div>
              <label className="text-sm text-zinc-300 mb-2 block">Color</label>
              <div className="grid grid-cols-3 gap-2">
                {(["white", "random", "black"] as const).map((color) => (
                  <button
                    key={color}
                    onClick={() => setHumanColor(color)}
                    className={`p-3 rounded border-2 transition capitalize font-semibold ${
                      humanColor === color
                        ? "border-blue-500 bg-blue-500 bg-opacity-10"
                        : "border-zinc-600 hover:border-zinc-500"
                    }`}
                  >
                    {color}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Step 4: Confirmation */}
        {step === 4 && (
          <div>
            <h2 className="text-xl font-bold text-white mb-4">
              Ready to Play?
            </h2>
            <div className="bg-zinc-700 rounded p-4 space-y-2 mb-6 text-sm">
              <div>
                <span className="text-zinc-400">Input Mode:</span>{" "}
                <span className="text-white font-semibold capitalize">{inputMode}</span>
              </div>
              <div>
                <span className="text-zinc-400">Game Mode:</span>{" "}
                <span className="text-white font-semibold capitalize">{gameMode}</span>
              </div>
              {gameMode === "single" && (
                <div>
                  <span className="text-zinc-400">Difficulty:</span>{" "}
                  <span className="text-white font-semibold">{elo}</span>
                </div>
              )}
              <div>
                <span className="text-zinc-400">Color:</span>{" "}
                <span className="text-white font-semibold capitalize">{humanColor}</span>
              </div>
            </div>
          </div>
        )}

        {/* Navigation Buttons */}
        <div className="flex gap-3 mt-8">
          {step > 1 && (
            <button
              onClick={handleBack}
              className="flex-1 px-4 py-2 bg-zinc-700 text-white rounded hover:bg-zinc-600 transition"
            >
              Back
            </button>
          )}
          {step < 4 && (
            <button
              onClick={handleNext}
              disabled={
                (step === 1 && !inputMode) ||
                (step === 2 && !gameMode)
              }
              className="flex-1 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition disabled:bg-zinc-600 disabled:cursor-not-allowed"
            >
              Next
            </button>
          )}
          {step === 4 && (
            <button
              onClick={handleStartGame}
              className="flex-1 px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 transition font-semibold"
            >
              Start Game
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
