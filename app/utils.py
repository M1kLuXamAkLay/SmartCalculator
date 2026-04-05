import re
from fractions import Fraction

SUBSCRIPT = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")


def preprocess_expr(raw: str) -> str:
    if not raw:
        return ""
    expr = (raw.replace('×', '*').replace('÷', '/')
            .replace('^', '**').replace('√', 'sqrt').replace('∫', 'integrate'))
    expr = re.sub(r'\|([^|]*)\|', r'Abs(\1)', expr)
    expr = re.sub(r'([^\s(]+)!', r'factorial(\1)', expr)

    def decimal_to_frac(match):
        try:
            return str(Fraction(match.group(0)).limit_denominator(10000))
        except:
            return match.group(0)
    expr = re.sub(r'\b\d+\.\d+\b', decimal_to_frac, expr)
    return expr


def nice_float(x):
    """Красивый вывод: terminating decimal → decimal, иначе точная форма (√, π, дробь)"""
    import sympy as sp
    if isinstance(x, (int, float)):
        f = float(x)
        if f.is_integer():
            return str(int(f))
        s = f"{f:.10g}"
        return s.rstrip('0').rstrip('.') if '.' in s else s

    if not hasattr(x, 'is_number'):
        return str(x)

    try:
        if x.is_integer:
            return str(int(x))
        if x.is_rational and x.is_real:
            f = float(x)
            # Если конечная десятичная дробь — показываем decimal
            if f == int(f) or len(str(f).split('.')[-1]) <= 6:
                s = f"{f:.10g}"
                return s.rstrip('0').rstrip('.') if '.' in s else s
            return str(x)  # иначе дробь

        if x.is_complex and not x.is_real:
            re_part = sp.re(x)
            im_part = sp.im(x)
            re_str = nice_float(re_part) if re_part != 0 else ''
            im_str = nice_float(im_part)
            if im_str == '1': im_str = ''
            elif im_str == '-1': im_str = '-'
            if re_str and im_str:
                sign = ' + ' if float(sp.re(im_part)) > 0 else ' - '
                if sign == ' - ' and im_str.startswith('-'):
                    im_str = im_str[1:]
                return re_str + sign + im_str + 'i'
            return (im_str if im_str else '0') + 'i' if not re_str else re_str

        s = str(sp.simplify(x))
        s = s.replace('**', '^').replace('sqrt', '√').replace('pi', 'π')
        return s
    except:
        return str(x)


def _format_periodic(imgset):
    """Чистая обработка ImageSet → «2kπ» или «π + 2kπ»"""
    try:
        import sympy as sp
        lam = imgset.args[0]
        dummy = lam.args[0]
        expr = lam.args[1]

        k = sp.symbols('k')
        clean = expr.subs(dummy, k)
        expanded = sp.expand(clean)                  # ← важно для π(2k+1) → π + 2kπ
        s = str(expanded).replace('pi', 'π').replace('**', '^')
        s = re.sub(r'\s*\*\s*', '', s)               # убираем все *

        # Переставляем слагаемые: константа первой (π + 2kπ)
        if '+' in s and 'k' in s and 'π' in s:
            terms = [t.strip() for t in s.split('+')]
            const = next((t for t in terms if 'k' not in t), None)
            coeff = next((t for t in terms if 'k' in t), None)
            if const and coeff:
                s = f"{const} + {coeff}"

        return s
    except:
        return str(imgset)


def format_solution(sols, var_name="x"):
    """Финальное форматирование — ВСЁ красиво и корректно"""
    import sympy as sp

    if sols is False or not sols:
        return "Нет решений"
    if sols is True:
        return f"{var_name} ∈ ℝ"

    # FiniteSet (обычные корни, ±√, комплексные)
    if isinstance(sols, sp.FiniteSet):
        lst = list(sols)
        if len(lst) == 1:
            return f"{var_name} = {nice_float(lst[0])}"
        if len(lst) == 2:
            a, b = sorted(lst, key=lambda z: float(sp.re(z) or 0))
            if b == -a and getattr(a, 'is_real', False):
                return f"{var_name} = ±{nice_float(sp.Abs(a))}"
        lines = [f"{var_name}{str(i).translate(SUBSCRIPT)} = {nice_float(s)}"
                 for i, s in enumerate(lst[:6], 1)]
        return "\n".join(lines)

    # y = x + 5 и подобные
    if isinstance(sols, sp.Intersection):
        if len(sols.args) == 2 and isinstance(sols.args[0], sp.FiniteSet):
            return format_solution(sols.args[0], var_name)

    # Периодические решения (sin, cos, tan и т.д.)
    if isinstance(sols, sp.ImageSet):
        return f"{var_name} = {_format_periodic(sols)}, k ∈ ℤ"

    # Union двух периодических ветвей (sin(x)=0, cos(x)=0 и т.п.)
    if isinstance(sols, sp.Union) and all(isinstance(a, sp.ImageSet) for a in sols.args):
        parts = [_format_periodic(item) for item in sols.args]
        if len(parts) == 2:
            return f"{var_name}₁ = {parts[0]}, k ∈ ℤ\n{var_name}₂ = {parts[1]}, k ∈ ℤ"
        return "\n".join(f"{var_name} = {p}, k ∈ ℤ" for p in parts)

    # Интервалы
    if isinstance(sols, sp.Interval):
        left = '-∞' if sols.left.is_infinite else nice_float(sols.left)
        right = '+∞' if sols.right.is_infinite else nice_float(sols.right)
        l_br = '(' if sols.left_open else '['
        r_br = ')' if sols.right_open else ']'
        return f"{var_name} ∈ {l_br}{left}; {right}{r_br}"

    return str(sols)


# ===================== Остальные функции (без изменений) =====================
def get_sympy_locals(x, y=None):
    import sympy as sp
    from sympy import pi, E, I
    d = {"π": pi, "pi": pi, "e": E, "I": I, "i": I,
         "x": x, "Abs": sp.Abs, "factorial": sp.factorial,
         "ctg": sp.cot, "tan": sp.tan, "log": sp.log,
         "lg": lambda z: sp.log(z, 10), "ln": lambda z: sp.log(z, E),
         "integrate": lambda a, b, f: sp.integrate(f, (x, a, b)),
         "lim": lambda a, b, f: sp.limit(f, x, a, b if b in ['+', '-'] else '+')}
    if y is not None:
        d["y"] = y
    return d


def parse_math_expr(raw: str, var_symbol, y=None):
    if not raw:
        return None
    import sympy as sp
    from sympy.parsing.sympy_parser import parse_expr, standard_transformations, implicit_multiplication_application
    expr = preprocess_expr(raw)
    locals_dict = get_sympy_locals(var_symbol, y)
    try:
        return parse_expr(expr, local_dict=locals_dict,
                          transformations=standard_transformations + (implicit_multiplication_application,))
    except:
        return sp.sympify(expr, locals=locals_dict)


def detect_variable(eq_str: str) -> str:
    if not eq_str:
        return 'x'
    text = eq_str.lower()
    known = [r'\bsin\b', r'\bcos\b', r'\btan\b', r'\bctg\b', r'\bcot\b',
             r'\bln\b', r'\blog\b', r'\blg\b', r'\bsqrt\b', r'\babs\b',
             r'\bexp\b', r'\bfactorial\b', r'\bpi\b', r'\be\b']
    for p in known:
        text = re.sub(p, '', text)
    matches = re.findall(r'[a-z]', text)
    if not matches:
        return 'x'
    unique = list(dict.fromkeys(matches))
    return 'x' if 'x' in unique else unique[0]