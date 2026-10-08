def is_prime(n):
    """Перевірка простого числа."""
    if n <= 1:
        return False
    for i in range(2, int(n**0.5) + 1):
        if n % i == 0:
            return False
    return True

def factorial(n):
    """Обчислення факторіала."""
    if n < 0:
        raise ValueError("Факторіал від'ємного числа не існує")
    if n == 0 or n == 1:
        return 1
    result = 1
    for i in range(2, n + 1):
        result *= i
    return result

def is_even(n):
    """Перевірка парного числа."""
    return n % 2 == 0
