"""Trading Education (v0.6.2 Phase 9) — a ten-topic curriculum, ordered
as a real learning progression (candlesticks → wicks → trends →
support/resistance → ENTER/WAIT/AVOID → stop loss → take profit → risk/
reward → position sizing → why NO TRADE can be correct).

Lesson content is static curriculum text, not derived from live game
state — that's fine and honest (a definition of "what a wick means"
isn't game data to fabricate or verify, it's just teaching material).
Where a lesson maps onto a real TradeTown mechanic, it says so explicitly
and points at the real system (e.g. position sizing references the exact
formula in app/risk_engine.py's recommended_quantity(), the ENTER/WAIT/
AVOID lesson points at the real Command Center Overview chart) rather
than inventing a parallel example.

Never part of GameSaveState — only EducationProgress (what's been
viewed/completed) is real progress worth persisting.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.schemas import EducationLesson, EducationProgress, EducationTopic

MAX_QUIZ_ATTEMPTS_TRACKED = 500  # a generous ceiling on the two counters below, not a list to cap


@dataclass(frozen=True)
class _LessonSpec:
    id: EducationTopic
    order: int
    title: str
    simple_explanation: str
    visual_example_note: str
    deeper_explanation: str
    quiz_question: str
    quiz_options: tuple[str, str, str, str]
    correct_index: int


_LESSONS: tuple[_LessonSpec, ...] = (
    _LessonSpec(
        id="candlesticks",
        order=1,
        title="Reading a Candlestick",
        simple_explanation="Each candle shows four prices for one time period: open, high, low, and close. A green (bullish) candle closed higher than it opened; a red (bearish) candle closed lower.",
        visual_example_note="Open the Command Center's Overview tab and look at the live chart — every bar there is a real candle from the exact same data this lesson describes, not a picture.",
        deeper_explanation="The thick part is the 'body' (open-to-close range); the thin lines above/below are 'wicks' (the high/low reached before pulling back). A long body means strong conviction in one direction during that period.",
        quiz_question="A candle's body is colored green. What does that tell you?",
        quiz_options=("It closed higher than it opened", "It closed lower than it opened", "Volume was unusually high", "The stock is a good buy"),
        correct_index=0,
    ),
    _LessonSpec(
        id="wicks",
        order=2,
        title="What Wicks Tell You",
        simple_explanation="A wick (or 'shadow') is the thin line above or below a candle's body. It shows the highest and lowest prices reached, even if the price didn't stay there.",
        visual_example_note="On the Overview chart, find a candle with a long wick on one side — that's a period where price was pushed hard one way, then rejected back.",
        deeper_explanation="A long upper wick after a rally often means buyers pushed price up but sellers took control before the close — a warning sign, not a guarantee. Wicks are about rejection, bodies are about conviction.",
        quiz_question="A candle has a long wick on top and a small body near the bottom. What does the long upper wick suggest?",
        quiz_options=("Price was pushed up, then rejected back down", "The stock split", "Volume was zero", "It's guaranteed to keep falling"),
        correct_index=0,
    ),
    _LessonSpec(
        id="trends",
        order=3,
        title="Trends vs. Ranges",
        simple_explanation="A trend is a sustained move in one direction (higher highs and higher lows for an uptrend, the reverse for a downtrend). A range is price bouncing between a ceiling and a floor with no clear direction.",
        visual_example_note="TradeTown's own Signal Calibration mini-game (Command Center → TRAINING, Level 3) grades you on telling trending markets from ranging ones using this exact real chart data — a good next step after this lesson.",
        deeper_explanation="TradeTown's own regime read (used by both Signal Calibration and Player vs AI) calls a symbol 'trending' when its move is more than about 2x its own average volatility — otherwise it's 'ranging'. Trading a range like a trend is one of the most common beginner mistakes.",
        quiz_question="Price has been bouncing between $48 and $52 for two weeks with no clear direction. What is this called?",
        quiz_options=("A downtrend", "A range", "An uptrend", "A breakout"),
        correct_index=1,
    ),
    _LessonSpec(
        id="support_resistance",
        order=4,
        title="Support and Resistance",
        simple_explanation="Support is a price level where buying pressure has repeatedly stopped a decline. Resistance is a level where selling pressure has repeatedly stopped a rally.",
        visual_example_note="Watch the same symbol on the Overview chart across a few in-game days — a price level the chart keeps bouncing off of (in either direction) is acting as support or resistance.",
        deeper_explanation="These levels aren't exact lines, they're zones — and once broken, old resistance often becomes new support (and vice versa). They matter because they're where other traders are also watching, which can become a self-fulfilling reaction.",
        quiz_question="A stock has fallen to $40 three separate times this month and bounced higher each time. $40 is acting as:",
        quiz_options=("Resistance", "Support", "A stop loss", "A dividend date"),
        correct_index=1,
    ),
    _LessonSpec(
        id="enter_wait_avoid",
        order=5,
        title="ENTER, WAIT, or AVOID",
        simple_explanation="Every trade decision comes down to three honest options: ENTER (the setup is good enough to act on now), WAIT (not enough evidence yet, but stay watching), or AVOID (the setup is bad or the risk isn't worth it).",
        visual_example_note="This is exactly the choice TradeTown's real Signal Calibration mini-game and Player vs AI feature ask you to make on real data — practice it there once you're comfortable with this lesson.",
        deeper_explanation="'WAIT' is not indecision — it's a real, disciplined answer when the signals are mixed or the risk/reward isn't clear yet. Acting only when you truly have an edge, and waiting the rest of the time, is what separates a plan from a guess.",
        quiz_question="The trend is unclear, volatility is unusually high, and there's no strong signal either way. What's the most disciplined call?",
        quiz_options=("ENTER — something is better than nothing", "WAIT — not enough evidence yet", "AVOID forever — never look at this symbol again", "Double the position size to be safe"),
        correct_index=1,
    ),
    _LessonSpec(
        id="stop_loss",
        order=6,
        title="Stop Loss Orders",
        simple_explanation="A stop loss is an order that automatically exits a position if price moves against you past a set point — it caps how much a single trade can lose.",
        visual_example_note="TradeTown's own order types include a real 'stop_loss' order type (see the Command Center's paper trading system) — it's not a theoretical concept here, it's a real order the AI agents place.",
        deeper_explanation="A stop loss turns an unknown, open-ended risk into a known, bounded one, decided *before* emotions are involved in the moment. Setting it too tight risks being stopped out by normal noise; too loose defeats the purpose.",
        quiz_question="What is the main purpose of a stop loss order?",
        quiz_options=("To guarantee a profit", "To cap how much a single trade can lose", "To increase position size automatically", "To predict the next trend"),
        correct_index=1,
    ),
    _LessonSpec(
        id="take_profit",
        order=7,
        title="Take Profit Orders",
        simple_explanation="A take profit is an order that automatically exits a position once it reaches a target gain — it locks in a win instead of hoping for more and giving it back.",
        visual_example_note="Like stop loss, 'take_profit' is a real order type TradeTown's own paper trading engine supports — check a closed trade's details in the Command Center's Decisions tab to see one in action.",
        deeper_explanation="A take profit level is usually set using the same risk/reward thinking as a stop loss — if you're risking $1 to make $2, your take profit should reflect that 2x target, decided up front rather than chased after the fact.",
        quiz_question="What does a take profit order do?",
        quiz_options=("Cancels the trade for free", "Automatically exits once a target gain is reached", "Increases the stop loss distance", "Only works on losing trades"),
        correct_index=1,
    ),
    _LessonSpec(
        id="risk_reward",
        order=8,
        title="Risk/Reward Ratio",
        simple_explanation="Risk/reward compares how much you stand to lose against how much you stand to gain on a trade. A 1:2 ratio means risking $1 to potentially make $2.",
        visual_example_note="Signal Calibration's Level 2 grades exactly this — weighing a real move against its own volatility before deciding ENTER/WAIT/AVOID.",
        deeper_explanation="A good risk/reward ratio means you can be wrong more often than you're right and still come out ahead over many trades. It's why 'was this trade a winner' matters less than 'was the ratio good before you knew the outcome'.",
        quiz_question="You're risking $50 to potentially make $150 on a trade. What is the risk/reward ratio?",
        quiz_options=("1:1", "1:3", "3:1", "1:5"),
        correct_index=1,
    ),
    _LessonSpec(
        id="position_sizing",
        order=9,
        title="Position Sizing",
        simple_explanation="Position sizing decides how much of a portfolio goes into a single trade — even a great setup can hurt you badly if the position is too large.",
        visual_example_note="TradeTown's own Sentinel agent sizes every real paper trade using the exact same idea: risking a fixed % of equity per trade, capped at a max position %, whichever is smaller.",
        deeper_explanation="Sizing every trade the same regardless of confidence is a common mistake — but so is betting huge on a single 'sure thing'. A fixed risk-per-trade rule keeps any one bad trade from doing lasting damage.",
        quiz_question="Why does TradeTown's risk engine size every position using a fixed % of equity per trade?",
        quiz_options=("So every trade wins", "So one bad trade can't cause outsized damage", "To guarantee maximum profit", "Because larger positions are always safer"),
        correct_index=1,
    ),
    _LessonSpec(
        id="no_trade_ok",
        order=10,
        title="Why NO TRADE Can Be Correct",
        simple_explanation="Not trading is a real, valid decision — not a failure to act. If the setup, risk, or evidence isn't there, sitting it out protects capital for the next real opportunity.",
        visual_example_note="Check the Command Center's Decisions tab — TradeTown's own AI logs plenty of real 'NO TRADE' outcomes, each with its own honest reasoning, right alongside the trades it did take.",
        deeper_explanation="A trading record isn't just measured by wins and losses on trades taken — avoiding a real loser by correctly passing is just as valuable, even though it never shows up as a P&L number. Confusing activity with progress is one of the costliest habits to unlearn.",
        quiz_question="An AI agent reviews a setup and logs a real 'NO TRADE' decision. Does this always mean the AI 'did nothing useful'?",
        quiz_options=("Yes — it should always find a way to trade", "No — correctly avoiding a bad setup is a valid, useful outcome", "Only if the stock later goes up", "Only if a human overrides it"),
        correct_index=1,
    ),
)

_BY_ID: dict[str, _LessonSpec] = {lesson.id: lesson for lesson in _LESSONS}


def default_education_progress() -> EducationProgress:
    return EducationProgress()


def all_lessons() -> list[EducationLesson]:
    """Ordered curriculum, public shape (no answer key)."""
    return [
        EducationLesson(
            id=lesson.id,
            order=lesson.order,
            title=lesson.title,
            simpleExplanation=lesson.simple_explanation,
            visualExampleNote=lesson.visual_example_note,
            deeperExplanation=lesson.deeper_explanation,
            quizQuestion=lesson.quiz_question,
            quizOptions=list(lesson.quiz_options),
        )
        for lesson in sorted(_LESSONS, key=lambda spec: spec.order)
    ]


def mark_viewed(progress: EducationProgress, lesson_id: str) -> EducationProgress:
    if lesson_id not in _BY_ID or lesson_id in progress.viewed_lesson_ids:
        return progress
    return progress.model_copy(update={"viewed_lesson_ids": [*progress.viewed_lesson_ids, lesson_id]})


def grade_quiz(progress: EducationProgress, lesson_id: str, selected_index: int) -> tuple[EducationProgress, bool, int, str] | None:
    """Returns (new_progress, correct, correct_index, correct_option) or
    None if lesson_id doesn't exist."""
    lesson = _BY_ID.get(lesson_id)
    if lesson is None:
        return None

    correct = selected_index == lesson.correct_index
    completed_ids = progress.completed_lesson_ids
    if correct and lesson_id not in completed_ids:
        completed_ids = [*completed_ids, lesson_id]

    new_progress = progress.model_copy(
        update={
            "completed_lesson_ids": completed_ids,
            "quiz_attempts": min(progress.quiz_attempts + 1, MAX_QUIZ_ATTEMPTS_TRACKED),
            "correct_quiz_attempts": min(progress.correct_quiz_attempts + (1 if correct else 0), MAX_QUIZ_ATTEMPTS_TRACKED),
        }
    )
    return new_progress, correct, lesson.correct_index, lesson.quiz_options[lesson.correct_index]
