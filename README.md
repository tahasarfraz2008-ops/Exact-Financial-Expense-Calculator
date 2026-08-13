# Exact Financial Arithmetic Engine

A lossless, rational-arithmetic financial calculation engine, built as a foundation for integration into a Python banking/financial application.

> **This is a foundation, not a complete banking system.** A real production banking platform needs additional regulatory, security, accounting, currency, concurrency, and compliance controls well beyond an arithmetic engine — see [Limitations](#18-limitations).

---

## 1. What this project is

A Python engine that performs financial calculations **without losing precision at any intermediate step**. Every value inside the engine is stored as an exact rational number (a numerator over a denominator), never as a rounded decimal and never as a binary floating-point number. Rounding only ever happens when something explicitly asks for it, and every rounding operation records the original exact value, the rounded value, and the difference between them.

## 2. Why ordinary floating-point arithmetic is unsuitable

Binary floating point (`float` in Python, IEEE-754 double precision) represents numbers in base 2. Many ordinary decimal fractions — including `1/3`, `1/10`, and plenty of everyday monetary amounts — have no *exact* base-2 representation. Every `float` arithmetic operation on such a value carries a small, silent rounding error. Individually these errors are tiny; accumulated across thousands of transactions, they become real, auditable discrepancies in a bank's books.

## 3. What precision loss means

Precision loss is not "a slightly different-looking number" — it is the permanent destruction of information. Once a calculation replaces `100/3` with `33.33`, there is no way to recover the original `100` from any further arithmetic on `33.33`. The exact value is gone, forever, from that point in the calculation forward.

## 4. Why `100 / 3` is important

`100 / 3` is the simplest possible example of a division that does not terminate in decimal. It is the canonical stress-test for "does this system preserve exact values," because any system that rounds even slightly too early will fail to recover `100` when the result is multiplied back by `3`.

## 5. Why `33.33 * 3 = 99.99`

`33.33` is a rounded *approximation* of `100/3` — specifically, `100/3` rounded down to two decimal places. `33.33 * 3` is a perfectly correct multiplication of the number `33.33`; the problem is that `33.33` was never the right number to be multiplying in the first place. `33.33 ≠ 100/3`. The error was introduced the moment the rounding happened, not at the multiplication step — the multiplication merely reveals it.

## 6. How rational arithmetic solves the problem

Python's `fractions.Fraction` stores a number as an exact numerator and denominator, both arbitrary-precision integers. `Fraction(100, 3)` is not an approximation of `100/3` — it *is* `100/3`, exactly, and stays exact through any number of `+`, `-`, `*`, `/` operations, because combining two exact fractions always produces another exact fraction. This project's `ExactNumber` value object wraps `Fraction` and forbids raw `float` from entering the system at all (see `app/domain/value_objects/exact_number.py`).

## 7. Difference between `Fraction` and `Decimal`

| | `Fraction` (`ExactNumber`) | `Decimal` |
|---|---|---|
| Represents | Any rational number exactly | A fixed-point decimal number, to a chosen precision |
| `1/3` | Exact, forever | Must eventually be rounded to some number of digits |
| Best used for | Internal calculation, where the *true mathematical value* must never be lost | Final monetary amounts, where a business rule fixes the number of decimal places (e.g. 2 for USD) |
| This project's rule | Use for calculation precision | Use for monetary/display precision, and only via the explicit rounding service |

The engine does **not** blindly use `Fraction` for every banking operation — see the next section.

## 8. Difference between exact calculation and monetary rounding

- **Exact calculation** (`ExactNumber`, backed by `Fraction`): the true mathematical result of an expression, with no decimal-place limit. `100.00 / 3` has the exact result `100/3`.
- **Monetary settlement/rounding** (`Money.settle()`, `RoundingPolicy`): the real amount that would actually be transferred, booked, or paid, in a currency's smallest legal unit (e.g. cents). `100.00 USD / 3` cannot be paid out as `33.333...` — a business rule must decide how the leftover fraction of a cent is distributed. This project handles that via the **allocation service** (`app/domain/services/allocation_service.py`), which uses the largest-remainder method to split an exact total into real, payable parts that sum *exactly* back to the original total (e.g. `33.33 / 33.33 / 33.34`).

The system **never** confuses the two: an exact result is always available even after a settlement has been computed, and a settlement is never treated as if it were the authoritative exact value.

## 9. Architecture

Clean Architecture, with dependencies pointing inward (infrastructure and presentation depend on application and domain; domain depends on nothing else in this project):

```
exact_financial_engine/
│
├── app/
│   ├── domain/                     # Pure business rules. No framework/DB imports.
│   │   ├── entities/                # Money, FinancialCalculation, CalculationResult, CalculationAudit
│   │   ├── value_objects/           # ExactNumber, Currency, RoundingPolicy
│   │   ├── services/                # rounding, display, expression eval, allocation, interest, FX
│   │   └── exceptions/              # The named financial-safety exception hierarchy
│   │
│   ├── application/                 # Orchestrates domain logic for specific use cases.
│   │   ├── use_cases/                # EvaluateExpression, RoundValue, ConvertCurrency
│   │   ├── dto/                      # Plain data-transfer objects crossing layer boundaries
│   │   └── interfaces/               # Repository ports (abstract), implemented by infrastructure
│   │
│   ├── infrastructure/               # Concrete, swappable implementations of the ports above.
│   │   ├── repositories/              # In-memory (default/tests) and SQLAlchemy (MySQL/SQLite)
│   │   ├── persistence/               # Database engine/table setup
│   │   └── logging/                   # Operational logging configuration
│   │
│   └── presentation/                 # The outermost layer -- talks to the outside world.
│       ├── api/                       # FastAPI app, routes, Pydantic schemas
│       ├── cli/                       # Terminal demonstration script
│       └── web/                       # Self-contained interactive HTML demo
│
├── tests/
│   ├── unit/                          # Domain value objects & services in isolation
│   ├── integration/                   # Use cases + FastAPI endpoints, end to end
│   └── financial/                     # The exact regression scenarios required by spec
│
├── docs/                              # Additional documentation
├── requirements.txt
├── pyproject.toml
├── README.md
└── .gitignore
```

**Why this shape?** Each folder answers one question the spec explicitly asked for a clean answer to:
- *domain*: "what is true about money and exact numbers, independent of any technology?"
- *application*: "what can a caller ask this system to do?"
- *infrastructure*: "how do we actually store/log things, today?" (swappable without touching the above)
- *presentation*: "how does the outside world talk to this?" (HTTP, CLI, or browser — interchangeable)

## 10. Core domain model

| Object | Why it exists |
|---|---|
| `ExactNumber` | The exact, `Fraction`-backed rational number every calculation is built from. |
| `Money` | A currency-bound amount — pairs an `ExactNumber` with a `Currency`, and is the only place settlement rounding happens. |
| `Currency` | A registry of supported currencies and their settlement decimal-place business rule (e.g. USD → 2, JPY → 0). |
| `RoundingPolicy` | A named, explicit rounding rule (`HALF_UP`, `HALF_EVEN`, `DOWN`, `UP`, `FLOOR`, `CEILING`) — never an implicit default. |
| `FinancialCalculation` | A single request to evaluate an expression — "what was asked." |
| `CalculationResult` | The outcome of a calculation — the exact result plus its display rendering. |
| `CalculationAudit` | A full, explainable record of one calculation for regulatory/support purposes. |

## 11. `ExactNumber`

See `app/domain/value_objects/exact_number.py`. Supports `+ - * /` and full comparisons, all delegating to `Fraction`. Raw `float` is rejected at construction and at every arithmetic operation, via `AccidentalFloatError` — this is the project's core safety guarantee made structural rather than merely a convention.

```python
a = ExactNumber("100")
b = ExactNumber("3")
result = a / b        # 100/3, exact
result * b            # 100, exact
```

## 12. Expression calculator

See `app/domain/services/expression_evaluator.py`. A hand-written tokenizer plus recursive-descent parser — **not `eval()`** (see [Security](#16-security-considerations)) — implementing standard operator precedence:

```
expression := term (('+' | '-') term)*
term       := factor (('*' | '/') factor)*
factor     := NUMBER | '(' expression ')' | '-' factor
```

`term` is nested inside `expression`, which is why `2 + 3 * 4` evaluates to `14`: multiplication/division bind tighter than addition/subtraction. Parentheses recurse back into `expression`, which lets them override that default precedence.

## 13. Decimal display

See `app/domain/services/decimal_display.py`. `to_display_string(value, digits)` renders an `ExactNumber` as a string with a chosen number of digits, flagging whether the value is a repeating decimal. Changing `digits` never changes the underlying `ExactNumber` — display and storage are fully decoupled.

## 14. Exact vs. approximate results

Every API response and CLI demonstration explicitly labels a result as exact (`is_exact: true`, and `is_repeating` tells you whether the *displayed* decimal digits are the full story or a truncated approximation of a repeating decimal). A finite-looking decimal display is never claimed to be the full exact value when it isn't.

## 15. Banking use cases demonstrated

- **Account balances**: deposits/withdrawals kept as running `ExactNumber` totals.
- **Interest**: `simple_interest` (`Principal × Rate × Time`) and `compound_interest`, both exact for a whole number of compounding periods (`app/domain/services/interest_service.py`).
- **Loans**: `build_amortization_schedule` walks a loan period by period, carrying the *exact* remaining balance forward between rows (never re-deriving it from a previously-rounded value), while also exposing a currency-settled view of each row.
- **Currency conversion**: `convert()` (`app/domain/services/currency_conversion_service.py`) applies an exact exchange rate and keeps the converted amount unrounded until an explicit `.settle()` call.
- **Transaction splitting**: `allocate()` (`app/domain/services/allocation_service.py`) splits an exact total into real, payable parts via the largest-remainder method, guaranteeing the parts sum exactly back to the total.

## 16. Security considerations

User-supplied expressions are **never** passed to Python's `eval()`. `eval()` executes arbitrary Python with the full permissions of the process — a malicious "expression" like `__import__('os').system(...)` handed to `eval()` would run that command. This project uses a hand-written tokenizer + recursive-descent parser (see [Section 12](#12-expression-calculator)) that only understands digits, `+ - * / ( )`, and whitespace; there is no code path from user input to arbitrary code execution. All other inputs (currency codes, rounding-mode names, decimal-place counts) are validated against explicit allow-lists / registries and rejected with a named exception rather than silently coerced.

## 17. Banking safety guardrails

Custom exceptions (`app/domain/exceptions/financial_exceptions.py`) cover: division by zero, invalid numbers/expressions, invalid or mismatched currencies, invalid rounding modes, negative values where a business rule forbids them, accidental `float` use, and silent rounding. Every one of these is a specific, catchable type — never a bare exception or a swallowed error.

## 18. Limitations

This project is an **arithmetic and persistence-shape foundation**, not a complete banking system. It deliberately does *not* implement: authentication/authorization, double-entry ledger enforcement, transaction atomicity/concurrency control beyond what SQLAlchemy gives for free, live exchange-rate sourcing, regulatory reporting, fraud detection, or multi-currency account modeling beyond the `Money`/`Currency` types shown here. Numerators/denominators are stored as unbounded text columns; a production system should decide and enforce a maximum digit length to avoid pathological inputs consuming excessive storage or CPU.

## 19. Future improvements

Idempotency keys for calculation submission; a proper migrations tool (Alembic) instead of `metadata.create_all`; pluggable currency-rate providers; configurable maximum expression length/complexity; async database access; structured audit-log querying/export; more currencies and locale-aware display formatting.

---

## Installation

Requires Python 3.12+.

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Environment setup

By default the engine runs with **zero external setup**: the API uses in-memory repositories, and the SQL-backed repositories default to a local SQLite file. To use MySQL instead, set:

```bash
export DATABASE_URL="mysql+pymysql://user:password@localhost:3306/financial_engine"
```

## Running the application

**REST API:**

```bash
uvicorn app.presentation.api.main:app --reload
```

Then open `http://127.0.0.1:8000/docs` for interactive API documentation.

**CLI demonstration:**

```bash
python -m app.presentation.cli.demo
```

**Desktop GUI calculator:**

```bash
python -m app.presentation.gui.calculator_app
```

Tkinter ships with the standard Windows/macOS Python installer, so no extra install is needed there. On Linux, install your distro's Tk bindings first, e.g. `sudo apt install python3-tk`. The GUI has a full button grid, an adjustable-precision decimal readout, a "Settle as Money" panel (currency + rounding-mode selection with the rounding difference always shown), a calculation history you can click back through, and an "Explain this result" button that opens a plain-language walkthrough of the exact formulas (fraction addition/subtraction/multiplication/division, GCD reduction, long-division decimal display, and quantize-based rounding) used to produce whatever is currently on screen.

**Interactive HTML demo:** open `app/presentation/web/demo.html` directly in a browser — it is fully self-contained (a small BigInt-based fraction implementation in the page itself) and needs no server.

## Running tests

```bash
pytest                      # full suite
pytest tests/financial       # just the required precision-regression scenarios
pytest --cov=app             # with coverage
mypy app                     # static type checking
```

## API documentation

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/v1/calculations` | Evaluate an expression, return exact + display result |
| `GET`  | `/api/v1/calculations/{id}` | Retrieve a previously computed calculation |
| `POST` | `/api/v1/round` | Explicitly round an exact value under a named policy |
| `POST` | `/api/v1/convert` | Convert Money between currencies, exact + settled |
| `GET`  | `/api/v1/health` | Liveness check |

Example:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/calculations \
  -H "Content-Type: application/json" \
  -d '{"expression": "100 / 3 * 3"}'
```

```json
{
  "calculation_id": "…",
  "expression": "100 / 3 * 3",
  "exact_result": "100",
  "decimal_result": "100",
  "is_exact": true,
  "is_repeating": false
}
```

```bash
curl -X POST http://127.0.0.1:8000/api/v1/calculations \
  -H "Content-Type: application/json" \
  -d '{"expression": "100 / 3", "display_digits": 20}'
```

```json
{
  "exact_result": "100/3",
  "decimal_result": "33.33333333333333333333...",
  "is_exact": true,
  "is_repeating": true
}
```

## Database setup

Uses **MySQL** in production (via SQLAlchemy + PyMySQL), SQLite for local development/tests with no extra setup. Tables: `calculations`, `calculation_operations`, `currencies`, `rounding_policies`, `audit_logs` (see `app/infrastructure/persistence/database.py`).

**The authoritative result is never stored as only a rounded decimal.** Exact rational values are stored as separate `numerator`/`denominator` text columns, so the true value can always be reconstructed losslessly — see the detailed advantages/disadvantages discussion in that module's docstring.

For MySQL:

```sql
CREATE DATABASE financial_engine CHARACTER SET utf8mb4;
```

```bash
export DATABASE_URL="mysql+pymysql://user:password@localhost:3306/financial_engine"
```

Tables are created automatically on first use via `metadata.create_all()`.

## Final demonstration

```
INPUT:              100 / 3
EXACT:               100/3
DECIMAL DISPLAY:     33.333333333333333333333333...

THEN:                (100/3) × 3
RESULT:              100
STATUS:              EXACT — NO INTERMEDIATE ROUNDING

INPUT:               1/3 + 1/3 + 1/3
RESULT:              1
```

Reproduce this yourself: `python -m app.presentation.cli.demo`.
