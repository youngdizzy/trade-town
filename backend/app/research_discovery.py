"""app/research_discovery.py — CEO directive "TradeTown — Phase 8:
Autonomous Strategy Discovery + Adversarial Research Engine." The one
real orchestrator wiring `app/strategy_families.py` (Section 8A-8C:
diverse population generation, deterministic, duplicate-pruned) and
`app/adversarial_research.py` (Section 8D-8I: attack every real
survivor, derive real failure boundaries) together, over the exact same
unmodified real funnel `app/research_loop.py::run_research_loop_iteration()`
already provides — no second backtest engine, no second compiler, no
second candidacy gate.

SCOPE BOUNDARY, DISCLOSED. This module deliberately runs ONE real
generation per population member (compile -> backtest -> adversarial
attack -> classify), never `app/research_factory.py`'s own full
recursive multi-generation mutation-evolution per candidate — a 10-30
candidate population, each independently evolved across up to 5
generations, would multiply real backtest+adversarial compute by 5-10x
per candidate for a single manual research action, which this pass
judged an unreasonable default cost for "generate and triage a diverse
population." Any individual promising candidate this module surfaces
can still be hand-picked and evolved further via the existing,
completely unmodified `POST /research-factory/run`
(`run_research_factory_cycle()`).

THE SCORECARD NEVER OVERRIDES A HARD GATE. `classify_research_scorecard()`
below is a real, disclosed, priority-ordered rule: the existing
`CandidacyBinning` from `app/research_loop.py::classify_candidacy()` (the
research-candidate gate — >=100 trades / <=20% drawdown / PF >1.10 /
etc., itself deliberately never touching Certification/Hall-of-Fame/
Champion-Challenger) is checked FIRST and is the ONLY thing that can
produce `"rejected"` — no adversarial finding, no lesson, no similarity
result, and no research score can ever downgrade a `"rejected"`
candidacy back up, or upgrade past it. Adversarial evidence (outlier/
regime/extended-cost resilience) can only ever REFINE an "accepted"/
"promising" candidacy into a finer-grained real read
(fragile/promising/robust/champion_candidate) — it is a strictly
ADDITIVE, informational overlay, exactly matching Section 8I's own
explicit "never allow the classification itself to override a hard
gate" instruction, proven by `tests/test_research_discovery.py`'s own
dedicated hard-gate-bypass-impossible test.

LESSON-DRIVEN DISCOVERY REASONS (Section 8K). `discovery_reason` is a
real, structured (never free-text-only) field on every generated
candidate: `"successful_family"` when this family's own real,
already-computed `FamilyResearchStats.average_expectancy_r` was
positive BEFORE this cycle ran (a real prior, not a post-hoc
rationalization); `"research_exploration"` otherwise — the honest
default for a fresh, non-mutated population member. The richer, per-
mutation reasons (`failed_cost_resilience`/`failed_regime`/etc.) are
real and already wired for the Phase 7 mutation-chain path (see
`app/research_factory.py::generate_next_hypothesis()`'s own
`reasonForGeneration`); this module's own population members have no
single parent failure code to attribute a reason to, since they are
independently generated, not mutated.
"""
from __future__ import annotations

import statistics

from app.adversarial_research import evaluate_holdout_availability, run_adversarial_research
from app.champion_challenger import ChampionRecord
from app.quant_research_lab import QuantResearchExperiment
from app.research_factory import derive_lifecycle_stage
from app.research_loop import generate_research_lesson, run_research_loop_iteration
from app.schemas import (
    AdversarialResearchResult,
    AgentId,
    CompiledStrategyDefinition,
    DiscoveryReason,
    FactoryCandidateRecord,
    FailedStrategyArchiveEntry,
    FamilyResearchStats,
    ResearchAllocationDecision,
    ResearchDiscoveryCycleRecord,
    ResearchLessonRecord,
    ResearchLoopIterationRecord,
    ResearchScorecardClassification,
    StrategyFamily,
    StrategyHypothesis,
)
from app.strategy_engine import DEFAULT_CANDLES_PER_SYMBOL, DEFAULT_TIMEFRAME
from app.strategy_families import SUPPORTED_FAMILIES, allocate_research_budget, generate_candidate_population, prune_duplicates
from app.strategy_registry import register_strategy_version

# Section 8S — a real, disclosed, bounded population cap.
MAX_POPULATION_SIZE = 30
MIN_POPULATION_SIZE = 1


def classify_research_scorecard(
    candidacy: str,
    adversarial_result: AdversarialResearchResult | None,
) -> tuple[ResearchScorecardClassification, str]:
    """Section 8I — see this module's own docstring for the exact,
    disclosed, never-overridable priority order."""
    if candidacy in ("rejected", "overfit", "benchmark_failed", "risk_failed", "duplicate"):
        return "rejected", f"Real candidacy '{candidacy}' already fails the existing research-candidate gate — no adversarial evidence can override a hard gate."
    if candidacy == "insufficient_evidence":
        return "fragile", "Below the real evidence floor for a candidacy decision — real adversarial attacks are not yet meaningful either."
    if candidacy == "promising":
        return "promising", "Clears most, but not yet every, real research-candidate requirement."
    # candidacy == "accepted" from here — the existing gate is cleared;
    # adversarial evidence may only refine, never revert, this read.
    if adversarial_result is None:
        return "promising", "Clears the existing research-candidate gate but has not yet been adversarially attacked."
    if adversarial_result.outlier_resilience.classification == "highly_outlier_dependent":
        return "fragile", "Clears the existing gate, but real expectancy depends on the real top 1% of winning trades — highly outlier-dependent."
    if adversarial_result.regime_robustness.classification == "regime_fragile":
        return "fragile", "Clears the existing gate, but shows real negative/zero expectancy in every real, sufficiently-evidenced regime tested."
    if adversarial_result.extended_cost_attack.survives_beyond_stress is False:
        return "fragile", "Clears the existing gate, but real expectancy fails under the real extended (beyond-stressed) cost attack."
    if (
        adversarial_result.outlier_resilience.classification == "robust_to_outliers"
        and adversarial_result.regime_robustness.classification == "regime_robust"
        and adversarial_result.extended_cost_attack.survives_beyond_stress is True
    ):
        return "champion_candidate", "Clears the existing gate AND survives every real adversarial attack this module runs (outlier removal, regime, extended cost)."
    return "robust", "Clears the existing gate and most real adversarial attacks, without qualifying for the full champion-candidate bar."


def compute_family_research_stats(
    all_candidates: list[FactoryCandidateRecord], *, families: tuple[StrategyFamily, ...] = SUPPORTED_FAMILIES
) -> list[FamilyResearchStats]:
    """Section 8J — real, computed-fresh (never persisted, never
    stale) per-family statistics over every real candidate this
    codebase has ever generated for each family."""
    by_family: dict[StrategyFamily, list[FactoryCandidateRecord]] = {f: [] for f in families}
    for candidate in all_candidates:
        if candidate.research_family is not None and candidate.research_family in by_family:
            by_family[candidate.research_family].append(candidate)

    stats: list[FamilyResearchStats] = []
    for family in families:
        candidates = by_family[family]
        backtested = [c for c in candidates if c.iteration is not None]
        rejected = [c for c in candidates if c.lifecycle_stage in ("rejected", "compile_rejected", "duplicate_pruned")]
        promising = [c for c in backtested if c.iteration is not None and c.iteration.candidacy == "promising"]
        robust = [c for c in backtested if c.scorecard_classification in ("robust", "champion_candidate")]
        expectancies = [c.iteration.scorecard.expectancy_r for c in backtested if c.iteration is not None and c.iteration.scorecard.expectancy_r is not None]
        drawdowns = [c.iteration.scorecard.max_drawdown_r for c in backtested if c.iteration is not None and c.iteration.scorecard.max_drawdown_r is not None]
        beats_benchmark = [
            c for c in backtested if c.iteration is not None and c.iteration.benchmark_comparisons and all(b.beats_benchmark for b in c.iteration.benchmark_comparisons)
        ]
        cost_resilient = [c for c in backtested if c.iteration is not None and c.iteration.scorecard.cost_sensitivity_verdict == "cost_resilient"]
        wf_pass = [c for c in backtested if c.iteration is not None and c.iteration.scorecard.walk_forward_verdict == "stable"]
        adversarial_survivors = [c for c in backtested if c.adversarial_result is not None and c.adversarial_result.extended_cost_attack.survives_beyond_stress]
        stats.append(
            FamilyResearchStats(
                family=family,
                numberGenerated=len(candidates),
                numberBacktested=len(backtested),
                numberRejected=len(rejected),
                numberPromising=len(promising),
                numberRobust=len(robust),
                averageExpectancyR=(round(sum(expectancies) / len(expectancies), 4) if expectancies else None),
                medianExpectancyR=(round(statistics.median(expectancies), 4) if expectancies else None),
                averageMaxDrawdownR=(round(sum(drawdowns) / len(drawdowns), 4) if drawdowns else None),
                benchmarkBeatRatePct=(round(len(beats_benchmark) / len(backtested) * 100, 1) if backtested else None),
                costSurvivalRatePct=(round(len(cost_resilient) / len(backtested) * 100, 1) if backtested else None),
                walkForwardPassRatePct=(round(len(wf_pass) / len(backtested) * 100, 1) if backtested else None),
                adversarialSurvivalRatePct=(round(len(adversarial_survivors) / len(backtested) * 100, 1) if backtested else None),
            )
        )
    return stats


def run_research_discovery_cycle(
    *,
    concept_name: str,
    population_size: int,
    seed: str,
    compiled_strategy_registry: dict[str, list[CompiledStrategyDefinition]],
    quant_research_experiments: list[QuantResearchExperiment],
    research_iterations: list[ResearchLoopIterationRecord],
    research_lessons: list[ResearchLessonRecord],
    failed_archive: list[FailedStrategyArchiveEntry],
    champion_history: list[ChampionRecord],
    existing_candidates: list[FactoryCandidateRecord],
    risk_per_trade_pct: float,
    cycle_id: str,
    created_at: str,
    proposed_by: AgentId,
    families: tuple[StrategyFamily, ...] = SUPPORTED_FAMILIES,
    symbols: list[str] | None = None,
    timeframe: str | None = None,
    candles_per_symbol: int | None = None,
) -> tuple[ResearchDiscoveryCycleRecord, dict[str, list[CompiledStrategyDefinition]], list[ResearchLoopIterationRecord], list[ResearchLessonRecord]]:
    """Section 8B's one real entry point — see this module's own
    docstring for the complete real architecture and disclosed scope
    boundary. Pure function, matching this codebase's own established
    app/*.py-is-pure/app/state.py-persists-under-lock convention: never
    mutates shared state, returns the full real result set for the
    caller (app/state.py) to persist under its own lock."""
    resolved_timeframe = timeframe if timeframe is not None else DEFAULT_TIMEFRAME
    resolved_candles = candles_per_symbol if candles_per_symbol is not None else DEFAULT_CANDLES_PER_SYMBOL
    resolved_population_size = max(MIN_POPULATION_SIZE, min(population_size, MAX_POPULATION_SIZE))

    prior_family_stats = {s.family: s for s in compute_family_research_stats(existing_candidates, families=families)}

    registry = compiled_strategy_registry
    all_iterations = list(research_iterations)
    all_lessons = list(research_lessons)
    candidates: list[FactoryCandidateRecord] = []
    candidate_by_index: dict[int, str] = {}

    raw_population = generate_candidate_population(seed=seed, population_size=resolved_population_size, families=families)
    kept, duplicate_of_index = prune_duplicates(raw_population)
    kept_indexes = {c.index for c in kept}

    for seed_candidate in raw_population:
        candidate_id = f"{cycle_id}-candidate-{seed_candidate.index}"
        candidate_by_index[seed_candidate.index] = candidate_id

        if seed_candidate.index not in kept_indexes:
            duplicate_of_candidate_id = candidate_by_index.get(duplicate_of_index[seed_candidate.index])
            candidates.append(
                FactoryCandidateRecord(
                    id=candidate_id,
                    runId=cycle_id,
                    generation=0,
                    parentCandidateId=None,
                    lineageId=cycle_id,
                    strategyFamily=f"{concept_name} — {seed_candidate.family} #{seed_candidate.index}",
                    definitionId="",
                    definitionVersion=0,
                    hypothesis=_placeholder_hypothesis(seed_candidate, proposed_by=proposed_by, timeframe=resolved_timeframe, created_at=created_at),
                    lifecycleStage="duplicate_pruned",
                    compileStatus="ambiguous",
                    compileDetail="Not compiled — pruned as a real near-duplicate before spending real research budget.",
                    iteration=None,
                    mutationCandidate=None,
                    survived=False,
                    decisionReason=f"Real word-overlap near-duplicate of candidate '{duplicate_of_candidate_id}' — never backtested (Section 8C).",
                    createdAt=created_at,
                    researchFamily=seed_candidate.family,
                    candidateSeed=seed_candidate.candidate_seed,
                    discoveryReason="research_exploration",
                    duplicateOfCandidateId=duplicate_of_candidate_id,
                )
            )
            continue

        strategy_name = f"{concept_name} — {seed_candidate.family} #{seed_candidate.index}"
        definition, registry = register_strategy_version(registry, name=strategy_name, source_text=seed_candidate.source_text, timeframe=resolved_timeframe, created_by=proposed_by)
        prior_stats = prior_family_stats.get(seed_candidate.family)
        discovery_reason: DiscoveryReason = "successful_family" if prior_stats is not None and prior_stats.average_expectancy_r is not None and prior_stats.average_expectancy_r > 0 else "research_exploration"

        if definition.status != "compiled":
            candidates.append(
                FactoryCandidateRecord(
                    id=candidate_id,
                    runId=cycle_id,
                    generation=0,
                    parentCandidateId=None,
                    lineageId=cycle_id,
                    strategyFamily=strategy_name,
                    definitionId=definition.id,
                    definitionVersion=definition.version,
                    hypothesis=_placeholder_hypothesis(seed_candidate, proposed_by=proposed_by, timeframe=resolved_timeframe, created_at=created_at),
                    lifecycleStage="compile_rejected",
                    compileStatus=definition.status,
                    compileDetail=definition.detail,
                    iteration=None,
                    mutationCandidate=None,
                    survived=False,
                    decisionReason=f"Compilation status '{definition.status}': {definition.detail}",
                    createdAt=created_at,
                    researchFamily=seed_candidate.family,
                    candidateSeed=seed_candidate.candidate_seed,
                    discoveryReason=discovery_reason,
                )
            )
            continue

        hypothesis = StrategyHypothesis(
            id=f"{candidate_id}-hypothesis",
            hypothesis=f"{seed_candidate.family.replace('_', ' ').title()} — {seed_candidate.direction} — {', '.join(f'{k}={v}' for k, v in seed_candidate.params.items())}",
            marketMechanism=f"Real family template '{seed_candidate.family}' — see app/strategy_families.py.",
            expectedEdge="See real candidate scorecard once backtested.",
            invalidationConditions="Fails the real research-candidate gate or a real adversarial attack.",
            symbolUniverse=symbols or [],
            timeframe=resolved_timeframe,
            entryConditions="See compiled definition.",
            exitConditions="See compiled definition.",
            stopLossLogic="See compiled definition.",
            takeProfitLogic="See compiled definition.",
            positionSizingLogic="Fixed risk per trade (CEO-configured RiskLimits.riskPerTradePct).",
            riskConstraints="Standard.",
            indicatorsFeatures=[],
            regimeAssumptions="",
            researchRationale=seed_candidate.research_reason,
            parentStrategyFamily=None,
            parentDefinitionId=None,
            parentDefinitionVersion=None,
            proposedBy=proposed_by,
            createdAt=created_at,
            generation=0,
            lineageId=cycle_id,
            reasonForGeneration=seed_candidate.research_reason,
            sourceEvidenceIds=[],
        )

        iteration = run_research_loop_iteration(
            hypothesis,
            definition,
            quant_research_experiments=quant_research_experiments,
            research_iterations=all_iterations,
            failed_archive=failed_archive,
            risk_per_trade_pct=risk_per_trade_pct,
            iteration_id=f"{candidate_id}-experiment",
            mutation_id=f"{candidate_id}-mutation-record",
            created_at=created_at,
            symbols=symbols,
            timeframe=resolved_timeframe,
            candles_per_symbol=resolved_candles,
        )
        all_iterations.append(iteration)

        lesson = generate_research_lesson(
            lesson_id=f"{candidate_id}-lesson",
            strategy_family=iteration.strategy_family,
            definition_id=definition.id,
            definition_version=definition.version,
            iteration_id=iteration.id,
            parent_definition_id=None,
            mutation_id=None,
            hypothesis=hypothesis.hypothesis,
            candidacy=iteration.candidacy,
            candidacy_reason=iteration.candidacy_reason,
            scorecard=iteration.scorecard,
            trade_count=iteration.scorecard.trade_count or 0,
            created_at=created_at,
        )
        all_lessons.append(lesson)

        adversarial_result = run_adversarial_research(
            definition,
            regime_trend_breakdown=iteration.experiment.backtest.regime_trend_breakdown,
            regime_volatility_breakdown=iteration.experiment.backtest.regime_volatility_breakdown,
            parameter_sensitivity=iteration.experiment.parameter_sensitivity,
            risk_per_trade_pct=risk_per_trade_pct,
            result_id=f"{candidate_id}-adversarial",
            generated_at=created_at,
            symbols=symbols,
            timeframe=resolved_timeframe,
            candles_per_symbol=resolved_candles,
        )

        lifecycle_stage = derive_lifecycle_stage(compile_status=definition.status, candidacy=iteration.candidacy)
        scorecard_classification, scorecard_reason = classify_research_scorecard(iteration.candidacy, adversarial_result)
        survived = lifecycle_stage == "survivor"

        candidates.append(
            FactoryCandidateRecord(
                id=candidate_id,
                runId=cycle_id,
                generation=0,
                parentCandidateId=None,
                lineageId=cycle_id,
                strategyFamily=strategy_name,
                definitionId=definition.id,
                definitionVersion=definition.version,
                hypothesis=hypothesis,
                lifecycleStage=lifecycle_stage,
                compileStatus=definition.status,
                compileDetail=definition.detail,
                iteration=iteration,
                mutationCandidate=None,
                survived=survived,
                decisionReason=f"{iteration.candidacy_reason} Scorecard: {scorecard_classification} — {scorecard_reason}",
                createdAt=created_at,
                researchFamily=seed_candidate.family,
                candidateSeed=seed_candidate.candidate_seed,
                discoveryReason=discovery_reason,
                adversarialResult=adversarial_result,
                scorecardClassification=scorecard_classification,
            )
        )

    survivor_ids = [c.id for c in candidates if c.survived]
    champion_ids = [c.id for c in candidates if c.scorecard_classification == "champion_candidate"]
    duplicates_pruned_count = len(raw_population) - len(kept)

    family_stats = compute_family_research_stats([*existing_candidates, *candidates], families=families)
    allocation = allocate_research_budget(family_stats)
    allocation_decisions = [ResearchAllocationDecision(family=f, allocationWeightPct=weight, rationale=rationale) for f, weight, rationale in allocation]

    stop_reason = (
        f"Generated {len(raw_population)} candidate(s) across {len(families)} real, compiler-supported families; "
        f"{duplicates_pruned_count} pruned as real near-duplicates; {len(survivor_ids)} real survivor(s), "
        f"{len(champion_ids)} real champion-candidate(s)."
    )

    record = ResearchDiscoveryCycleRecord(
        id=cycle_id,
        conceptName=concept_name,
        populationSize=resolved_population_size,
        seed=seed,
        candidates=candidates,
        familyStats=family_stats,
        allocationDecisions=allocation_decisions,
        survivorCandidateIds=survivor_ids,
        championCandidateIds=champion_ids,
        duplicatesPruned=duplicates_pruned_count,
        stopReason=stop_reason,
        holdout=evaluate_holdout_availability(),
        createdAt=created_at,
    )
    return record, registry, all_iterations, all_lessons


def _placeholder_hypothesis(seed_candidate, *, proposed_by: AgentId, timeframe: str, created_at: str) -> StrategyHypothesis:
    """A real, minimal `StrategyHypothesis` for a candidate pruned or
    rejected before a full one was ever built — never left `None`
    (the schema requires one), never claims to be more than what it is."""
    return StrategyHypothesis(
        id=f"{seed_candidate.candidate_seed}-hypothesis",
        hypothesis=f"{seed_candidate.family.replace('_', ' ').title()} — {seed_candidate.direction}.",
        marketMechanism=f"Real family template '{seed_candidate.family}'.",
        expectedEdge="Not evaluated.",
        invalidationConditions="Not evaluated.",
        symbolUniverse=[],
        timeframe=timeframe,
        entryConditions="See source text.",
        exitConditions="See source text.",
        stopLossLogic="See source text.",
        takeProfitLogic="See source text.",
        positionSizingLogic="Fixed risk per trade.",
        riskConstraints="Standard.",
        indicatorsFeatures=[],
        regimeAssumptions="",
        researchRationale=seed_candidate.research_reason,
        parentStrategyFamily=None,
        parentDefinitionId=None,
        parentDefinitionVersion=None,
        proposedBy=proposed_by,
        createdAt=created_at,
        generation=0,
        lineageId=None,
        reasonForGeneration=seed_candidate.research_reason,
        sourceEvidenceIds=[],
    )
