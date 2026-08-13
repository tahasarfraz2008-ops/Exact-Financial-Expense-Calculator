"""
Advanced GUI calculator (desktop presentation layer).

WHAT IS IT?
-----------
A Tkinter desktop application exposing the engine's exact-arithmetic
domain services (the SAME functions the REST API and CLI demo call --
`evaluate_expression`, `round_exact_number`, `to_display_string`,
`Money.settle`) behind a full calculator GUI: a button grid, a live
exact-fraction readout, an adjustable-precision decimal readout, a
calculation history panel, and a currency-settlement panel with a
rounding-mode selector.

WHY TKINTER?
------------
Tkinter ships in the Python standard library on Windows (no extra
install step), which matches this project's "runs with zero external
setup" principle and fits a Windows-desktop delivery target. No GUI
framework dependency needs to be added to requirements.txt for this
to run.

WHY DOES THIS BELONG IN `app/presentation/gui`?
--------------------------------------------------
Same Clean Architecture rule as the rest of the project: presentation
code (Tkinter widgets, event handlers, layout) is the outermost layer
and depends inward on the domain layer -- it never reimplements
arithmetic itself. Every number this GUI shows was computed by
`app.domain.services.*`, not by ad hoc code in a button callback.

HOW DOES IT WORK, AT A GLANCE?
--------------------------------
- Button presses append tokens to an expression string shown in the
  "Expression" field (exactly like a physical calculator's tape).
- Pressing "=" calls `evaluate_expression()` (the same safe,
  eval()-free parser used everywhere else in this project) and shows:
    * the EXACT result, as a reduced fraction (numerator/denominator)
    * a DECIMAL rendering of that fraction, to a user-adjustable
      number of digits, via `to_display_string()`
    * whether the decimal rendering is exact or a truncated repeating
      decimal
- The "Settle as Money" panel takes the current exact result, wraps it
  in a `Money` for a chosen currency, and shows the real, roundable
  settlement amount for a chosen `RoundingPolicy` -- along with the
  precise difference the rounding introduced (never silent).
- "Explain" opens a window that walks through the exact formulas used
  for the calculation currently on screen (see `_build_explanation`),
  so the GUI is also a teaching tool, not just a black box.
"""

from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from tkinter import ttk

from app.domain.exceptions.financial_exceptions import FinancialEngineError
from app.domain.entities.money import Money
from app.domain.services.decimal_display import to_display_string
from app.domain.services.expression_evaluator import evaluate_expression
from app.domain.services.rounding_service import round_exact_number
from app.domain.value_objects.currency import Currency
from app.domain.value_objects.exact_number import ExactNumber
from app.domain.value_objects.rounding_policy import RoundingPolicy

# ----------------------------------------------------------------------
# Visual design tokens -- kept in one place so the whole GUI stays
# consistent (a "ledger" palette matching the project's web demo).
# ----------------------------------------------------------------------
BG = "#12201A"
PANEL_BG = "#1B2B23"
PAPER = "#F1ECE0"
ACCENT_GREEN = "#2E5A48"
ACCENT_TEAL = "#3E8E7E"
ACCENT_RED = "#C0473A"
MUTED = "#8AA79A"
FONT_DISPLAY = ("Consolas", 26, "bold")
FONT_MONO = ("Consolas", 13)
FONT_MONO_SMALL = ("Consolas", 11)
FONT_LABEL = ("Segoe UI", 10)
FONT_BUTTON = ("Segoe UI", 13)


@dataclass
class _HistoryEntry:
    expression: str
    exact_result: str
    decimal_result: str


class CalculatorApp(tk.Tk):
    """The main application window."""

    def __init__(self) -> None:
        super().__init__()
        self.title("Exact Financial Calculator")
        self.geometry("980x640")
        self.minsize(860, 560)
        self.configure(bg=BG)

        self._expression = tk.StringVar(value="")
        self._display_digits = tk.IntVar(value=20)
        self._last_exact_result: ExactNumber | None = None
        self._history: list[_HistoryEntry] = []

        self._build_layout()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------
    def _build_layout(self) -> None:
        root = ttk.Frame(self, padding=14)
        root.pack(fill="both", expand=True)
        root.columnconfigure(0, weight=3)
        root.columnconfigure(1, weight=2)
        root.rowconfigure(0, weight=1)

        self._build_calculator_column(root).grid(row=0, column=0, sticky="nsew", padx=(0, 14))
        self._build_side_column(root).grid(row=0, column=1, sticky="nsew")

    def _build_calculator_column(self, parent: ttk.Widget) -> ttk.Frame:
        column = ttk.Frame(parent)
        column.rowconfigure(2, weight=1)
        column.columnconfigure(0, weight=1)

        # --- expression / display ---
        display_frame = tk.Frame(column, bg=PANEL_BG, padx=16, pady=14)
        display_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        display_frame.columnconfigure(0, weight=1)

        tk.Label(
            display_frame, textvariable=self._expression, anchor="e",
            bg=PANEL_BG, fg=MUTED, font=FONT_MONO,
        ).grid(row=0, column=0, sticky="ew")

        self._exact_var = tk.StringVar(value="0")
        tk.Label(
            display_frame, textvariable=self._exact_var, anchor="e",
            bg=PANEL_BG, fg=PAPER, font=FONT_DISPLAY,
        ).grid(row=1, column=0, sticky="ew", pady=(4, 0))

        self._decimal_var = tk.StringVar(value="= 0")
        tk.Label(
            display_frame, textvariable=self._decimal_var, anchor="e",
            bg=PANEL_BG, fg=ACCENT_TEAL, font=FONT_MONO,
        ).grid(row=2, column=0, sticky="ew", pady=(2, 0))

        self._status_var = tk.StringVar(value="")
        tk.Label(
            display_frame, textvariable=self._status_var, anchor="e",
            bg=PANEL_BG, fg=ACCENT_RED, font=FONT_MONO_SMALL,
        ).grid(row=3, column=0, sticky="ew")

        # --- precision control ---
        precision_row = ttk.Frame(column)
        precision_row.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        ttk.Label(precision_row, text="Decimal digits shown:").pack(side="left")
        ttk.Spinbox(
            precision_row, from_=0, to=100, width=5, textvariable=self._display_digits,
            command=self._refresh_decimal_display,
        ).pack(side="left", padx=8)
        ttk.Button(precision_row, text="Explain this result", command=self._show_explanation).pack(
            side="right"
        )

        # --- button grid ---
        button_grid = tk.Frame(column, bg=BG)
        button_grid.grid(row=2, column=0, sticky="nsew")
        self._build_button_grid(button_grid)

        return column

    def _build_button_grid(self, parent: tk.Frame) -> None:
        rows = [
            ["(", ")", "⌫", "C"],
            ["7", "8", "9", "/"],
            ["4", "5", "6", "*"],
            ["1", "2", "3", "-"],
            ["0", ".", "=", "+"],
        ]
        for r in range(len(rows)):
            parent.rowconfigure(r, weight=1)
        for c in range(4):
            parent.columnconfigure(c, weight=1)

        for r, row in enumerate(rows):
            for c, label in enumerate(row):
                self._make_button(parent, label).grid(
                    row=r, column=c, sticky="nsew", padx=5, pady=5
                )

    def _make_button(self, parent: tk.Frame, label: str) -> tk.Button:
        operator_labels = {"/", "*", "-", "+", "="}
        if label == "=":
            bg, fg, active = ACCENT_TEAL, PAPER, "#4FA391"
        elif label == "C":
            bg, fg, active = ACCENT_RED, PAPER, "#D65A4C"
        elif label in operator_labels or label in ("(", ")"):
            bg, fg, active = ACCENT_GREEN, PAPER, "#3B6E58"
        else:
            bg, fg, active = PANEL_BG, PAPER, "#243A2F"

        button = tk.Button(
            parent, text=label, font=FONT_BUTTON, bg=bg, fg=fg,
            activebackground=active, activeforeground=PAPER,
            relief="flat", bd=0, command=lambda l=label: self._on_button(l),
        )
        return button

    def _build_side_column(self, parent: ttk.Widget) -> ttk.Frame:
        column = ttk.Frame(parent)
        column.rowconfigure(1, weight=1)
        column.columnconfigure(0, weight=1)

        settle_panel = self._build_settlement_panel(column)
        settle_panel.grid(row=0, column=0, sticky="ew", pady=(0, 12))

        history_panel = self._build_history_panel(column)
        history_panel.grid(row=1, column=0, sticky="nsew")

        return column

    def _build_settlement_panel(self, parent: ttk.Widget) -> tk.Frame:
        panel = tk.Frame(parent, bg=PANEL_BG, padx=14, pady=12)

        tk.Label(
            panel, text="SETTLE AS MONEY", bg=PANEL_BG, fg=MUTED, font=FONT_LABEL,
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))

        ttk.Label(panel, text="Currency").grid(row=1, column=0, sticky="w")
        self._currency_var = tk.StringVar(value="USD")
        ttk.Combobox(
            panel, textvariable=self._currency_var, width=8, state="readonly",
            values=["USD", "PKR", "EUR", "GBP", "JPY", "SAR", "AED", "KWD"],
        ).grid(row=1, column=1, sticky="e", pady=3)

        ttk.Label(panel, text="Rounding mode").grid(row=2, column=0, sticky="w")
        self._rounding_var = tk.StringVar(value="HALF_UP")
        ttk.Combobox(
            panel, textvariable=self._rounding_var, width=8, state="readonly",
            values=[p.name for p in RoundingPolicy],
        ).grid(row=2, column=1, sticky="e", pady=3)

        ttk.Button(panel, text="Settle", command=self._on_settle).grid(
            row=3, column=0, columnspan=2, sticky="ew", pady=(8, 8)
        )

        self._settled_var = tk.StringVar(value="—")
        self._difference_var = tk.StringVar(value="")
        tk.Label(
            panel, textvariable=self._settled_var, bg=PANEL_BG, fg=PAPER,
            font=("Consolas", 18, "bold"), anchor="w",
        ).grid(row=4, column=0, columnspan=2, sticky="w")
        tk.Label(
            panel, textvariable=self._difference_var, bg=PANEL_BG, fg=ACCENT_RED,
            font=FONT_MONO_SMALL, anchor="w",
        ).grid(row=5, column=0, columnspan=2, sticky="w")

        panel.columnconfigure(1, weight=1)
        return panel

    def _build_history_panel(self, parent: ttk.Widget) -> tk.Frame:
        panel = tk.Frame(parent, bg=PANEL_BG, padx=14, pady=12)
        panel.rowconfigure(1, weight=1)
        panel.columnconfigure(0, weight=1)

        tk.Label(
            panel, text="HISTORY", bg=PANEL_BG, fg=MUTED, font=FONT_LABEL,
        ).grid(row=0, column=0, sticky="w", pady=(0, 8))

        self._history_list = tk.Listbox(
            panel, bg="#0F1A15", fg=PAPER, font=FONT_MONO_SMALL,
            selectbackground=ACCENT_GREEN, borderwidth=0, highlightthickness=0,
        )
        self._history_list.grid(row=1, column=0, sticky="nsew")
        self._history_list.bind("<<ListboxSelect>>", self._on_history_select)

        scrollbar = ttk.Scrollbar(panel, orient="vertical", command=self._history_list.yview)
        scrollbar.grid(row=1, column=1, sticky="ns")
        self._history_list.configure(yscrollcommand=scrollbar.set)

        return panel

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------
    def _on_button(self, label: str) -> None:
        if label == "C":
            self._expression.set("")
            self._reset_result_display()
            return
        if label == "⌫":
            self._expression.set(self._expression.get()[:-1])
            return
        if label == "=":
            self._calculate()
            return
        self._expression.set(self._expression.get() + label)

    def _calculate(self) -> None:
        expression_text = self._expression.get().strip()
        if not expression_text:
            return
        try:
            exact_result = evaluate_expression(expression_text)
        except FinancialEngineError as exc:
            self._status_var.set(str(exc))
            return

        self._status_var.set("")
        self._last_exact_result = exact_result
        self._exact_var.set(str(exact_result))
        self._refresh_decimal_display()

        display = to_display_string(exact_result, self._display_digits.get())
        entry = _HistoryEntry(expression_text, str(exact_result), display.text)
        self._history.append(entry)
        self._history_list.insert(
            "end", f"{entry.expression}  =  {entry.exact_result}"
        )
        self._history_list.see("end")

        self._settled_var.set("—")
        self._difference_var.set("")

    def _refresh_decimal_display(self) -> None:
        if self._last_exact_result is None:
            return
        display = to_display_string(self._last_exact_result, self._display_digits.get())
        suffix = "  (repeating)" if display.is_repeating else ""
        self._decimal_var.set(f"= {display.text}{suffix}")

    def _reset_result_display(self) -> None:
        self._last_exact_result = None
        self._exact_var.set("0")
        self._decimal_var.set("= 0")
        self._status_var.set("")
        self._settled_var.set("—")
        self._difference_var.set("")

    def _on_settle(self) -> None:
        if self._last_exact_result is None:
            self._status_var.set("Calculate a result before settling it as money.")
            return
        try:
            currency = Currency.of(self._currency_var.get())
            policy = RoundingPolicy.from_name(self._rounding_var.get())
        except FinancialEngineError as exc:
            self._status_var.set(str(exc))
            return

        money = Money(self._last_exact_result, currency)
        rounding_result = money.settle(policy)

        self._settled_var.set(f"{rounding_result.rounded_value} {currency.code}")
        self._difference_var.set(
            f"rounding difference: {rounding_result.difference}"
        )

    def _on_history_select(self, _event: object) -> None:
        selection = self._history_list.curselection()
        if not selection:
            return
        entry = self._history[selection[0]]
        self._expression.set(entry.expression)
        self._last_exact_result = ExactNumber(entry.exact_result)
        self._exact_var.set(entry.exact_result)
        self._refresh_decimal_display()

    # ------------------------------------------------------------------
    # Explanation window
    # ------------------------------------------------------------------
    def _show_explanation(self) -> None:
        window = tk.Toplevel(self)
        window.title("How this result was calculated")
        window.geometry("640x560")
        window.configure(bg=PANEL_BG)

        text = tk.Text(
            window, bg="#0F1A15", fg=PAPER, font=FONT_MONO_SMALL,
            wrap="word", padx=16, pady=16, borderwidth=0,
        )
        text.pack(fill="both", expand=True, padx=12, pady=12)
        text.insert("1.0", self._build_explanation())
        text.configure(state="disabled")

    def _build_explanation(self) -> str:
        expr = self._expression.get() or "(no expression yet)"
        exact = self._exact_var.get()
        digits = self._display_digits.get()
        decimal = self._decimal_var.get()

        return f"""EXPRESSION
  {expr}

EXACT RESULT (as a reduced fraction)
  {exact}

DECIMAL DISPLAY ({digits} digits)
  {decimal}

--------------------------------------------------------------
HOW THE ENGINE CALCULATES THIS
--------------------------------------------------------------

1. PARSING (no eval(), ever)
   The expression is tokenized character by character, then parsed
   with a recursive-descent parser using this grammar, which is what
   makes '*' and '/' bind tighter than '+' and '-':

     expression := term (('+' | '-') term)*
     term       := factor (('*' | '/') factor)*
     factor     := NUMBER | '(' expression ')' | '-' factor

2. EVERY NUMBER IS A FRACTION
   Each numeric literal becomes an exact fraction n/d (a whole number
   is just n/1). No value is ever a binary float.

3. THE FOUR OPERATIONS, EXACTLY
   For two fractions a/b and c/d:

     Addition:        a/b + c/d = (a*d + c*b) / (b*d)
     Subtraction:      a/b - c/d = (a*d - c*b) / (b*d)
     Multiplication:   a/b * c/d = (a*c) / (b*d)
     Division:         a/b / c/d = (a*d) / (b*c)      [c != 0, d != 0]

4. REDUCTION TO LOWEST TERMS
   After every operation, the result is reduced using the greatest
   common divisor (Euclid's algorithm):

     g = gcd(numerator, denominator)
     numerator   = numerator   / g
     denominator = denominator / g

   This is why 10/6 becomes 5/3, not 10/6 -- and why the fraction
   never grows larger than it needs to be.

5. DECIMAL DISPLAY (a separate, non-destructive step)
   The exact fraction n/d is converted to a decimal string by long
   division: repeatedly multiply the remainder by 10 and take the
   next digit, up to the requested number of digits. If the division
   never terminates (i.e. the reduced denominator has a prime factor
   other than 2 or 5), the display is marked '(repeating)' and
   truncated -- but the stored EXACT value is untouched.

6. ROUNDING / SETTLEMENT (only when you press "Settle")
   Rounding uses Python's decimal.Decimal.quantize() under an
   explicitly named policy (HALF_UP, HALF_EVEN, DOWN, UP, FLOOR,
   CEILING) to a currency's fixed number of decimal places, and always
   reports the DIFFERENCE between the exact value and the rounded
   value -- rounding never happens silently anywhere in this engine.

WHY THIS MATTERS
  Because every step above stays in exact fraction arithmetic,
  something like (100 / 3) * 3 recovers exactly 100 -- not
  99.99999999999999, and not 99.99. Rounding only ever happens at the
  one explicit moment you ask for a settled, payable amount.
"""


def main() -> None:
    app = CalculatorApp()
    app.mainloop()


if __name__ == "__main__":
    main()
