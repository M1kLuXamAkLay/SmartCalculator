import re

SUBSCRIPT = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")


def preprocess_expr(raw: str) -> str:
    """Общая предобработка математического выражения для sympy (убраны дубликаты замен по всему проекту)."""
    if not raw:
        return ""
    expr = (raw.replace('×', '*')
            .replace('÷', '/')
            .replace('^', '**')
            .replace('√', 'sqrt')
            .replace('∫', 'integrate'))
    expr = re.sub(r'\|([^|]*)\|', r'Abs(\1)', expr)
    expr = re.sub(r'([^\s(]+)!', r'factorial(\1)', expr)
    return expr


def nice_float_real(f):
    try:
        f = float(f)
        if f.is_integer():
            return str(int(f))
        s = f"{f:.10g}"
        return s.rstrip('0').rstrip('.') if '.' in s else s
    except (TypeError, ValueError):
        return str(f)


def nice_float(x):
    """Ленивый импорт sympy"""
    import sympy as sp
    if not (hasattr(x, 'is_number') and x.is_number):
        return str(x)
    try:
        x = sp.N(x, 12)
        real = float(sp.re(x))
        imag = float(sp.im(x))
        if imag == 0:
            return nice_float_real(real)
        if real == 0:
            imag_str = nice_float_real(abs(imag))
            return imag_str + 'i' if imag >= 0 else '-' + imag_str + 'i'
        real_str = nice_float_real(real)
        imag_str = nice_float_real(abs(imag))
        sign = ' + ' if imag > 0 else ' - '
        return real_str + sign + imag_str + 'i'
    except:
        return str(x)


def get_sympy_locals(x, y=None):
    """Ленивый импорт sympy"""
    import sympy as sp
    from sympy import pi, E, I
    d = {
        "π": pi, "pi": pi, "e": E, "I": I, "i": I,
        "x": x,
        "Abs": sp.Abs,
        "factorial": sp.factorial,
        "ctg": sp.cot,
        "tan": sp.tan,
        "log": sp.log,
        "lg": lambda z: sp.log(z, 10),
        "ln": lambda z: sp.log(z, E),
        "integrate": lambda a, b, f: sp.integrate(f, (x, a, b)),
        "lim": lambda a, b, f: sp.limit(f, x, a, b if b in ['+', '-'] else '+'),
    }
    if y is not None:
        d["y"] = y
    return d


def parse_math_expr(raw: str, var_symbol, y=None):
    """Ленивый импорт sympy + использование общей preprocess_expr (убран дубликат парсинга)."""
    if not raw:
        return None
    import sympy as sp
    from sympy.parsing.sympy_parser import parse_expr, standard_transformations, implicit_multiplication_application
    expr = preprocess_expr(raw)
    locals_dict = get_sympy_locals(var_symbol, y)
    try:
        return parse_expr(
            expr,
            local_dict=locals_dict,
            transformations=standard_transformations + (implicit_multiplication_application,)
        )
    except Exception:
        try:
            return sp.sympify(expr, locals=locals_dict)
        except:
            raise


def detect_variable(eq_str: str) -> str:
    """Определяет переменную (любая буква a-z кроме e, i)"""
    matches = re.findall(r'[a-zA-Z]', eq_str)
    for char in matches:
        lower = char.lower()
        if lower not in ['e', 'i']:
            return lower
    return 'x'


def format_solution(sols, var_name="x"):
    """Ленивый импорт sympy"""
    import sympy as sp
    if sols is False or not sols:
        return "Нет решений"
    if sols is True:
        return f"{var_name} ∈ ℝ"

    # === НЕРАВЕНСТВО (интервалы) ===
    if isinstance(sols, sp.Interval):
        left = '-∞' if sols.left.is_infinite else nice_float(sols.left)
        right = '+∞' if sols.right.is_infinite else nice_float(sols.right)
        l_br = '(' if sols.left_open else '['
        r_br = ')' if sols.right_open else ']'
        return f"{var_name} ∈ {l_br}{left}; {right}{r_br}"

    if isinstance(sols, (sp.Union, sp.Or)):
        parts = []
        for item in sols.args:
            if isinstance(item, sp.Interval):
                left = '-∞' if item.left.is_infinite else nice_float(item.left)
                right = '+∞' if item.right.is_infinite else nice_float(item.right)
                l_br = '(' if item.left_open else '['
                r_br = ')' if item.right_open else ']'
                parts.append(f"{l_br}{left}; {right}{r_br}")
        if parts:
            return f"{var_name} ∈ " + " ∪ ".join(parts)
        return "Нет решений"

    # === УРАВНЕНИЕ (корни) ===
    if not isinstance(sols, (list, tuple)):
        sols = [sols]
    sols = [s for s in sols if s is not False and s is not True]
    if not sols:
        return "Нет решений"

    if len(sols) == 1:
        val = nice_float(sols[0]) if hasattr(sols[0], 'is_number') and sols[0].is_number else str(sols[0])
        return f"{var_name} = {val}"

    # Несколько корней — красиво x₁ = , x₂ = ...
    lines = []
    for i, s in enumerate(sols[:6], 1):
        val = nice_float(s) if hasattr(s, 'is_number') and s.is_number else str(s)
        lines.append(f"{var_name}{str(i).translate(SUBSCRIPT)} = {val}")
    return "\n".join(lines)