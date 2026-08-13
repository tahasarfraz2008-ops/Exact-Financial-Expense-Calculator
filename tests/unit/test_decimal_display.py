from app.domain.services.decimal_display import to_display_string
from app.domain.value_objects.exact_number import ExactNumber


def test_repeating_decimal_flagged_and_truncated():
    display = to_display_string(ExactNumber("100") / ExactNumber("3"), digits=6)
    assert display.is_repeating is True
    assert display.text.startswith("33.333333")
    assert display.text.endswith("...")


def test_terminating_decimal_not_flagged_when_it_fits():
    display = to_display_string(ExactNumber("1") / ExactNumber("4"), digits=2)
    assert display.is_repeating is False
    assert display.text == "0.25"


def test_display_does_not_mutate_internal_value():
    exact = ExactNumber("100") / ExactNumber("3")
    to_display_string(exact, digits=2)
    to_display_string(exact, digits=50)
    # the internal fraction is immutable and unaffected by how many times
    # (or with what precision) it has been displayed
    assert str(exact) == "100/3"


def test_display_precision_does_not_change_internal_value():
    exact = ExactNumber("100") / ExactNumber("3")
    short = to_display_string(exact, digits=2)
    long = to_display_string(exact, digits=20)
    assert short.text != long.text
    assert str(exact) == "100/3"
