import type {
  AgentEnergy,
  AnalystChoice,
  Candle,
  CeoDecisionRecord,
  Debate,
  EducationLesson,
  EducationProgress,
  GameSaveState,
  GatekeeperRejection,
  KnowledgeGraph,
  PaperPortfolio,
  PlayerVsAiPrompt,
  PlayerVsAiState,
  QuestionOfTheDay,
  SavingsRuleType,
  SignalCalibrationState,
  SignalChallenge,
  SignalChoice,
  TimeAdvanceTarget,
  TradeDecision,
  TradeProposal,
  TreasuryState,
  WhatIfSimulation,
} from "@/types";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    let detail = body;
    try {
      const parsed = JSON.parse(body) as { detail?: string };
      if (parsed.detail) detail = parsed.detail;
    } catch {
      // body wasn't JSON (or had no `detail`) — fall back to the raw text above
    }
    throw new Error(detail || `[api] ${init?.method ?? "GET"} ${path} failed: ${res.status}`);
  }
  return (await res.json()) as T;
}

export const api = {
  loadGame: () => request<GameSaveState>("/load"),
  saveGame: (state: GameSaveState) =>
    request<{ ok: true; updatedAt: string }>("/save", {
      method: "POST",
      body: JSON.stringify(state),
    }),
  health: () => request<{ status: string }>("/health"),
  getCandles: (symbol: string, timeframe: string, limit = 150) =>
    request<Candle[]>(`/market/candles?symbol=${encodeURIComponent(symbol)}&timeframe=${encodeURIComponent(timeframe)}&limit=${limit}`),
  getTimeframes: () => request<string[]>("/market/timeframes"),
  spendEnergy: (action: string, researchId?: string) =>
    request<{ agentEnergy: AgentEnergy }>("/energy/spend", {
      method: "POST",
      body: JSON.stringify({ action, researchId: researchId ?? null }),
    }),
  getCalibrationChallenge: (level: number) => request<SignalChallenge>(`/calibration/challenge?level=${level}`),
  submitCalibrationChoice: (challengeId: string, choice: SignalChoice) =>
    request<{ signalCalibration: SignalCalibrationState; agentEnergy: AgentEnergy }>("/calibration/submit", {
      method: "POST",
      body: JSON.stringify({ challengeId, choice }),
    }),
  getPlayerVsAiPrompt: () => request<PlayerVsAiPrompt>("/player-vs-ai/prompt"),
  submitPlayerVsAiChoice: (promptId: string, choice: SignalChoice) =>
    request<{ playerVsAi: PlayerVsAiState }>("/player-vs-ai/submit", {
      method: "POST",
      body: JSON.stringify({ promptId, choice }),
    }),
  getLessons: () => request<EducationLesson[]>("/education/lessons"),
  markLessonViewed: (lessonId: string) =>
    request<{ education: EducationProgress }>("/education/view", {
      method: "POST",
      body: JSON.stringify({ lessonId }),
    }),
  submitQuiz: (lessonId: string, selectedIndex: number) =>
    request<{ correct: boolean; correctIndex: number; correctOption: string; education: EducationProgress }>("/education/quiz", {
      method: "POST",
      body: JSON.stringify({ lessonId, selectedIndex }),
    }),
  ackTradeNotification: (tradeId: string) =>
    request<{ viewedTradeNotificationIds: string[] }>("/trades/ack", {
      method: "POST",
      body: JSON.stringify({ tradeId }),
    }),
  submitCeoDecision: (proposalId: string, choice: AnalystChoice) =>
    request<{
      tradeProposals: TradeProposal[];
      ceoDecisions: CeoDecisionRecord[];
      decisions: TradeDecision[];
      paperPortfolio: PaperPortfolio;
      gatekeeperRejections: GatekeeperRejection[];
    }>("/executive/decide", {
      method: "POST",
      body: JSON.stringify({ proposalId, choice }),
    }),
  regenerateDebate: (proposalId: string) =>
    request<{ debates: Debate[] }>("/executive/debate/regenerate", {
      method: "POST",
      body: JSON.stringify({ proposalId }),
    }),
  getWhatIfSimulation: (symbol: string) => request<WhatIfSimulation>(`/executive/whatif?symbol=${encodeURIComponent(symbol)}`),
  getKnowledgeGraph: () => request<KnowledgeGraph>("/knowledge-graph"),
  submitQotdResponse: (questionId: string, response: string) =>
    request<{ question: QuestionOfTheDay }>("/mentor/qotd/respond", {
      method: "POST",
      body: JSON.stringify({ questionId, response }),
    }),
  depositTreasury: (amount: number) =>
    request<{ treasury: TreasuryState; paperPortfolio: PaperPortfolio }>("/treasury/deposit", {
      method: "POST",
      body: JSON.stringify({ amount }),
    }),
  withdrawTreasury: (amount: number) =>
    request<{ treasury: TreasuryState; paperPortfolio: PaperPortfolio }>("/treasury/withdraw", {
      method: "POST",
      body: JSON.stringify({ amount }),
    }),
  createSavingsRule: (ruleType: SavingsRuleType, percent: number, reserveTarget: number | null) =>
    request<{ treasury: TreasuryState }>("/treasury/rules/create", {
      method: "POST",
      body: JSON.stringify({ ruleType, percent, reserveTarget }),
    }),
  toggleSavingsRule: (ruleId: string, active: boolean) =>
    request<{ treasury: TreasuryState }>("/treasury/rules/toggle", {
      method: "POST",
      body: JSON.stringify({ ruleId, active }),
    }),
  pauseAllSavingsRules: () =>
    request<{ treasury: TreasuryState }>("/treasury/rules/pause-all", {
      method: "POST",
      body: JSON.stringify({}),
    }),
  advanceTime: (target: TimeAdvanceTarget, hours?: number) =>
    request<GameSaveState>("/time/advance", {
      method: "POST",
      body: JSON.stringify({ target, hours: hours ?? null }),
    }),
};
