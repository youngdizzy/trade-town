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

v0.7 Feature 49 (Phase 2) extends the curriculum with an eight-lesson
Liquidity/Market Structure module (orders 11-18), continuing the same
real progression from where the original ten leave off. Researched
first: this codebase has no order-book, bid/ask, trade-by-trade tape, or
liquidity-pool data anywhere (app/market_data.py's `Candle` is a single
aggregate OHLC bar with one volume number, uncorrelated with the bar's
own price move) — so every lesson in this module teaches the real
professional concept honestly, and either points at the one real
TradeTown mechanic that's the closest honest analog (the What-If
Simulation Lab's real "Liquidity Sweep" scenario for liquidity_sweeps;
the Scanner's real volume-confirmed breakout alert for
structure_shifts; the Trends/Support & Resistance lessons' own real
regime read for swing_structure/premium_discount) or explicitly
disclaims that no real detector exists for it in this simulation
(liquidity_basics, equal_highs_lows, inducement, order_flow_intro) —
never a fabricated one. The final lesson, order_flow_intro, exists
specifically to name that honesty boundary explicitly: every other
lesson in the module is really a way of *inferring* likely order flow
from price action alone, because the real order-by-order data isn't
available here.

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
    _LessonSpec(
        id="liquidity_basics",
        order=11,
        title="What Is Liquidity?",
        simple_explanation="Liquidity is where a lot of buy or sell orders are sitting, waiting to be filled. Price is often drawn toward these areas, because large orders need enough volume on the other side to fill without moving price too much.",
        visual_example_note="TradeTown has no real order-book or liquidity-pool feed to point to here — this lesson is conceptual, describing what a real broker's Level 2 data shows, which this simulation doesn't model.",
        deeper_explanation="Buy-side liquidity sits above price (stop orders from short sellers, breakout buy orders); sell-side liquidity sits below price (stop losses from long positions, breakout sell orders). Institutions with large orders often need these resting pools to fill their own size — part of why price is frequently drawn toward them before reversing.",
        quiz_question="Why does professional trading theory say price is often drawn toward areas of resting liquidity, like clusters of stop orders?",
        quiz_options=("Because liquidity always causes a reversal", "Because large orders often need that resting liquidity to fill their own size", "Because liquidity guarantees a profitable trade", "Because it has no effect on price"),
        correct_index=1,
    ),
    _LessonSpec(
        id="swing_structure",
        order=12,
        title="Swing Highs, Swing Lows & Market Structure",
        simple_explanation="A swing high is a peak where price turned down; a swing low is a trough where price turned up. A sequence of higher swing highs and higher swing lows defines an uptrend's structure — the reverse defines a downtrend.",
        visual_example_note="This builds on the Trends vs. Ranges lesson — the Overview chart's own real candles are exactly where you'd mark swing highs and lows by hand. TradeTown doesn't run a formal swing-detection algorithm, but that same lesson's real trend read tells you the net direction those swings are forming.",
        deeper_explanation="Market structure is the story swing highs and lows tell over time: as long as swings keep making higher highs and higher lows, structure is bullish. The first swing low that fails to hold — an old low getting broken — is the earliest real warning that structure may be shifting.",
        quiz_question="Price makes a new high, pulls back to a higher low than the previous pullback, then pushes to another new high. What does this sequence describe?",
        quiz_options=("A market structure shift", "Bullish market structure (higher highs, higher lows)", "A liquidity sweep", "A range"),
        correct_index=1,
    ),
    _LessonSpec(
        id="equal_highs_lows",
        order=13,
        title="Equal Highs, Equal Lows & Stop Clusters",
        simple_explanation="When price tests the same high (or low) more than once without breaking it, it forms 'equal highs' or 'equal lows' — a level many traders draw stops or breakout orders around, forming a real cluster of resting orders at that one price.",
        visual_example_note="TradeTown's simulated price data moves continuously and rarely lands on the exact same level twice, and there's no order-book feed to confirm a real stop cluster forming — this lesson describes what to look for on a real chart, not something this simulation detects for you.",
        deeper_explanation="Unlike a broader support/resistance zone, equal highs/lows are precise: the same near-exact level tested multiple times. That precision is exactly what makes them attractive to sweep — a lot of stops and breakout orders often sit clustered right above or below that one level.",
        quiz_question="A stock tests $50.00 resistance three times over two weeks, never closing above it, and traders start placing breakout buy stops just above $50.00. What is forming at that level?",
        quiz_options=("A support zone only", "A cluster of resting orders (stops/breakout orders)", "A dividend adjustment", "Nothing significant"),
        correct_index=1,
    ),
    _LessonSpec(
        id="liquidity_sweeps",
        order=14,
        title="Liquidity Sweeps & Grabs",
        simple_explanation="A liquidity sweep (or 'liquidity grab') is a fast move that pushes price just past a well-known high or low — triggering the stops and breakout orders resting there — before reversing hard the other way.",
        visual_example_note="TradeTown's own What-If Simulation Lab (open it while reviewing any real trade proposal in Executive Voting) already models this exact idea as its real 'Liquidity Sweep' scenario — a real hypothetical move scaled off that symbol's own measured volatility, honestly labeled a scenario rather than a claim that a sweep was actually detected.",
        deeper_explanation="The danger is assuming every push past a level is a sweep about to reverse — most of the time, a break of a level is just a break, and price keeps going. A real sweep is only confirmed after the fact, once price actually reverses hard; reacting to the mere possibility of one every time is how a real edge turns into overtrading.",
        quiz_question="Price spikes 2% above a well-known resistance level in seconds, triggering breakout buy stops, then reverses and closes back below that level within the hour. What does this describe?",
        quiz_options=("A confirmed breakout", "A liquidity sweep — the level was swept for stops, then price reversed", "A dividend payment", "A stock split"),
        correct_index=1,
    ),
    _LessonSpec(
        id="inducement",
        order=15,
        title="Inducement & Engineered Liquidity",
        simple_explanation="Inducement is a small, obvious move designed to lure traders into a position before the real move happens the other way. 'Engineered liquidity' describes resting orders that built up specifically because of an obvious, heavily-watched level.",
        visual_example_note="TradeTown has no real data on other market participants' intent or positioning — there's no way to actually confirm a move was 'engineered' rather than a genuine break. This lesson describes a professional concept to be aware of, not something this simulation can detect or verify.",
        deeper_explanation="The key discipline here is the same as with liquidity sweeps: inducement is a pattern to recognize in hindsight, not a signal to trade on its mere possibility. Assuming every obvious setup is a trap can be just as costly as assuming every setup is genuine — evidence and confirmation matter more than the theory alone.",
        quiz_question="Why should a trader be cautious about assuming every obvious, heavily-watched breakout level is 'inducement' set up to trap them?",
        quiz_options=("Because inducement never actually happens", "Because most breaks of a level are genuine, and assuming a trap every time has no more real evidence behind it than assuming a real breakout every time", "Because TradeTown detects inducement automatically", "Because inducement only happens on Mondays"),
        correct_index=1,
    ),
    _LessonSpec(
        id="structure_shifts",
        order=16,
        title="Market Structure Shifts & Displacement",
        simple_explanation="A market structure shift happens when price breaks a key swing high or low in the opposite direction of the prior trend, suggesting control has changed hands. Displacement is the strong, fast, high-momentum move that often accompanies a real structure shift, as opposed to a slow grind.",
        visual_example_note="TradeTown's real Scanner (Command Center alerts) already flags this exact combination — a 'breakout' alert only fires when a large price move is confirmed by a real volume spike in the same tick, the closest real signal this simulation has to true displacement.",
        deeper_explanation="A structure shift is a real, checkable event — a genuine break of a prior swing point — but confirming genuine displacement behind it, rather than a low-volume, easily-reversed poke through the level, is what separates a real shift from a fakeout. Scanner's own volume-spike requirement exists for exactly this reason.",
        quiz_question="An uptrend's price breaks below its most recent higher low, on a big volume spike. What does this combination suggest?",
        quiz_options=("The uptrend is definitely continuing", "A possible market structure shift, backed by real displacement (a volume-confirmed move)", "A dividend adjustment", "Nothing — volume doesn't matter"),
        correct_index=1,
    ),
    _LessonSpec(
        id="premium_discount",
        order=17,
        title="Premium and Discount Pricing",
        simple_explanation="Within a recent trading range, the upper half is considered 'premium' (relatively expensive, where sellers look to sell) and the lower half is considered 'discount' (relatively cheap, where buyers look to buy). The midpoint of the range is equilibrium.",
        visual_example_note="This is a more precise way of describing where inside a range price sits — the same 'range' concept from the Trends vs. Ranges lesson. TradeTown's own market regime read (Brain Room HUD) will call a symbol 'sideways' when it isn't trending, but doesn't split that range into premium/discount halves itself — that's a manual read you apply to the same real range you already know how to identify.",
        deeper_explanation="The idea isn't that discount always bounces and premium always drops — it's a bias: buyers preferentially look for reasons to buy in the discount half, and sellers preferentially look for reasons to sell in the premium half, all else being equal. It's a lens for weighing evidence, not a signal on its own.",
        quiz_question="A stock has been ranging between $40 (low) and $60 (high). At $45, where is price relative to premium/discount?",
        quiz_options=("In the premium half — expensive relative to the range", "In the discount half — cheap relative to the range", "Exactly at equilibrium", "Outside the range entirely"),
        correct_index=1,
    ),
    _LessonSpec(
        id="order_flow_intro",
        order=18,
        title="Order Flow: What It Is, and What TradeTown Can't Show You",
        simple_explanation="Order flow is the real-time record of actual buy and sell orders hitting the market — who's trading, how much, and at what price, moment to moment. Professional order-flow tools (like a real broker's Level 2 or Time & Sales) show this directly.",
        visual_example_note="TradeTown's own market data is a single aggregate OHLC candle per period, with one volume number per bar — there's no real order-book, no bid/ask, and no trade-by-trade tape anywhere in this simulation. This lesson exists so you understand the concept and its real limits here, not because TradeTown can show it to you.",
        deeper_explanation="Every other lesson in this Liquidity module — swing structure, equal highs/lows, sweeps, inducement, displacement, premium/discount — is really a way of *inferring* likely order flow from price action alone, when the real order-by-order data isn't available. That's a legitimate, widely-used approach in real trading, but it's important to know the difference between inferring flow from price and actually seeing it.",
        quiz_question="Why does this Liquidity module teach ways to infer buyer/seller behavior from price action instead of reading real order flow directly?",
        quiz_options=("Because order flow doesn't matter", "Because TradeTown's real market data is aggregate OHLC candles only — no order-book or trade-by-trade data exists in this simulation", "Because inferring from price is always more accurate", "Because real traders never use order flow"),
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
