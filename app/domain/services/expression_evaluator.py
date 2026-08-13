"""
Safe expression evaluator for financial arithmetic expressions.

WHAT IS IT?
-----------
A hand-written tokenizer + recursive-descent parser that evaluates
expressions like `100 / 3 * 3`, `(100 / 3) * 3`, or
`1 / 3 + 1 / 3 + 1 / 3`, producing an `ExactNumber` result -- without
ever calling Python's `eval()` on user input.

WHY DO WE NEED IT?
------------------
SECURITY (Section 21): `eval()` on user-supplied text executes
arbitrary Python code with the full permissions of the process running
it. A malicious "expression" like
`__import__('os').system('rm -rf /')` handed to `eval()` would run that
command. In a banking application, letting untrusted input reach
`eval()` is a critical remote-code-execution vulnerability, not a
theoretical concern. A hand-rolled parser that only understands
numbers, `+`, `-`, `*`, `/`, and parentheses has no way to do anything
other than arithmetic -- there is no code path to "execute" anything.

PRECISION (Sections 4, 12): the parser must never convert an
intermediate value to `float`. Every token that looks like a number is
parsed directly into an `ExactNumber` (Fraction-backed), and every
operation is performed on `ExactNumber`s all the way through.

HOW DOES IT WORK?
------------------
Classic two-stage design:

1. **Tokenizer** (`_tokenize`): walks the input string once,
   left-to-right, and produces a flat list of tokens: NUMBER, PLUS,
   MINUS, STAR, SLASH, LPAREN, RPAREN. Any character that isn't part of
   a recognised token raises `InvalidExpressionError` immediately --
   nothing is passed through un-validated.

2. **Recursive-descent parser** (`_Parser`): implements standard
   arithmetic operator precedence via three grammar levels, each
   calling the next:

   ```
   expression := term (('+' | '-') term)*
   term       := factor (('*' | '/') factor)*
   factor     := NUMBER | '(' expression ')' | '-' factor
   ```

   This structure is exactly why `2 + 3 * 4` evaluates to `14`, not
   `20`: `term` (which handles `*`/`/`) is nested *inside* `expression`
   (which handles `+`/`-`), so multiplication/division always bind
   more tightly than addition/subtraction, matching standard
   mathematical convention. Parentheses (`factor`) simply recurse back
   into `expression`, which is what lets them override precedence.

WHY THIS TECHNOLOGY?
---------------------
No third-party parsing library is used. The grammar this engine needs
(four arithmetic operators, unary minus, parentheses, numeric and
fractional literals) is small enough that a ~150-line hand-written
recursive-descent parser is easier to audit for security and
correctness than pulling in a general-purpose parser generator or
expression-evaluation library, and it keeps the "no eval, no arbitrary
code execution" guarantee fully inside code we can read end to end.

WHAT GOES WRONG IF IMPLEMENTED INCORRECTLY?
---------------------------------------------
An off-by-one in precedence handling would silently produce wrong
financial answers (e.g. treating `100 / 3 * 3` as `100 / (3 * 3)`).
Allowing any escape hatch back to `eval()` -- even "just for a special
case" -- reopens the remote-code-execution risk this module exists to
close.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

from app.domain.exceptions.financial_exceptions import InvalidExpressionError
from app.domain.value_objects.exact_number import ExactNumber


class _TokenType(Enum):
    NUMBER = auto()
    PLUS = auto()
    MINUS = auto()
    STAR = auto()
    SLASH = auto()
    LPAREN = auto()
    RPAREN = auto()
    EOF = auto()


@dataclass(frozen=True, slots=True)
class _Token:
    type: _TokenType
    text: str


_SINGLE_CHAR_TOKENS = {
    "+": _TokenType.PLUS,
    "-": _TokenType.MINUS,
    "*": _TokenType.STAR,
    "/": _TokenType.SLASH,
    "(": _TokenType.LPAREN,
    ")": _TokenType.RPAREN,
}

_ALLOWED_NUMBER_CHARS = set("0123456789.")


def _tokenize(expression: str) -> list[_Token]:
    tokens: list[_Token] = []
    i = 0
    length = len(expression)

    while i < length:
        char = expression[i]

        if char.isspace():
            i += 1
            continue

        if char in _SINGLE_CHAR_TOKENS:
            tokens.append(_Token(_SINGLE_CHAR_TOKENS[char], char))
            i += 1
            continue

        if char in _ALLOWED_NUMBER_CHARS:
            start = i
            seen_dot = char == "."
            i += 1
            while i < length and expression[i] in _ALLOWED_NUMBER_CHARS:
                if expression[i] == ".":
                    if seen_dot:
                        raise InvalidExpressionError(
                            f"Malformed number near position {i} in expression: {expression!r}"
                        )
                    seen_dot = True
                i += 1
            number_text = expression[start:i]
            if number_text in (".", ""):
                raise InvalidExpressionError(
                    f"Malformed number near position {start} in expression: {expression!r}"
                )
            tokens.append(_Token(_TokenType.NUMBER, number_text))
            continue

        raise InvalidExpressionError(
            f"Unexpected character {char!r} at position {i} in expression: {expression!r}. "
            "Only digits, '.', '+', '-', '*', '/', '(', ')' and whitespace are allowed."
        )

    tokens.append(_Token(_TokenType.EOF, ""))
    return tokens


class _Parser:
    """Recursive-descent parser implementing:

        expression := term (('+' | '-') term)*
        term       := factor (('*' | '/') factor)*
        factor     := NUMBER | '(' expression ')' | '-' factor
    """

    def __init__(self, tokens: list[_Token], original_expression: str) -> None:
        self._tokens = tokens
        self._position = 0
        self._original_expression = original_expression

    def parse(self) -> ExactNumber:
        result = self._expression()
        if self._current.type is not _TokenType.EOF:
            raise InvalidExpressionError(
                f"Unexpected token {self._current.text!r} after end of expression: "
                f"{self._original_expression!r}"
            )
        return result

    @property
    def _current(self) -> _Token:
        return self._tokens[self._position]

    def _advance(self) -> _Token:
        token = self._current
        self._position += 1
        return token

    def _expect(self, token_type: _TokenType) -> _Token:
        if self._current.type is not token_type:
            raise InvalidExpressionError(
                f"Expected {token_type.name} but found {self._current.text!r} "
                f"in expression: {self._original_expression!r}"
            )
        return self._advance()

    def _expression(self) -> ExactNumber:
        result = self._term()
        while self._current.type in (_TokenType.PLUS, _TokenType.MINUS):
            operator = self._advance()
            rhs = self._term()
            result = result + rhs if operator.type is _TokenType.PLUS else result - rhs
        return result

    def _term(self) -> ExactNumber:
        result = self._factor()
        while self._current.type in (_TokenType.STAR, _TokenType.SLASH):
            operator = self._advance()
            rhs = self._factor()
            result = result * rhs if operator.type is _TokenType.STAR else result / rhs
        return result

    def _factor(self) -> ExactNumber:
        if self._current.type is _TokenType.MINUS:
            self._advance()
            return -self._factor()

        if self._current.type is _TokenType.NUMBER:
            token = self._advance()
            return ExactNumber(token.text)

        if self._current.type is _TokenType.LPAREN:
            self._advance()
            result = self._expression()
            self._expect(_TokenType.RPAREN)
            return result

        raise InvalidExpressionError(
            f"Expected a number or '(' but found {self._current.text!r} "
            f"in expression: {self._original_expression!r}"
        )


def evaluate_expression(expression: str) -> ExactNumber:
    """Safely evaluate an arithmetic expression string into an exact
    `ExactNumber`, without using `eval()` and without ever converting
    any intermediate value to a raw `float`.
    """
    if not expression or not expression.strip():
        raise InvalidExpressionError("Expression must not be empty.")
    tokens = _tokenize(expression)
    parser = _Parser(tokens, expression)
    return parser.parse()
