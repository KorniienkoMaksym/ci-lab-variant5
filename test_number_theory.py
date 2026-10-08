import pytest
from number_theory import is_prime, factorial, is_even


def test_is_prime():
    assert is_prime(7) is True
    assert is_prime(4) is False
    assert is_prime(1) is False
    assert is_prime(-5) is False


def test_factorial():
    assert factorial(0) == 1
    assert factorial(1) == 1
    assert factorial(5) == 120


def test_factorial_negative():
    with pytest.raises(ValueError):
        factorial(-1)


def test_is_even():
    assert is_even(4) is True
    assert is_even(7) is False
    assert is_even(0) is True
    assert is_even(-2) is True
