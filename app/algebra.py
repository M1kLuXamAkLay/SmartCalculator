from utils import nice_float, get_sympy_locals, format_solution, detect_variable, parse_math_expr


def parse_relation(eq_str: str, var_symbol, y=None):
    import sympy as sp
    ops = ['<=', '>=', '<', '>', '=']
    for op in sorted(ops, key=len, reverse=True):
        if op in eq_str:
            left, right = eq_str.split(op, 1)
            l = parse_math_expr(left.strip(), var_symbol, y)
            r = parse_math_expr(right.strip(), var_symbol, y)
            if op == '<':  return sp.Lt(l, r, evaluate=False)
            if op == '>':  return sp.Gt(l, r, evaluate=False)
            if op == '<=': return sp.Le(l, r, evaluate=False)
            if op == '>=': return sp.Ge(l, r, evaluate=False)
            if op == '=':  return sp.Eq(l, r, evaluate=False)
    raise ValueError("Нет знака отношения")


def solve_single(eq_str: str) -> str:
    try:
        import sympy as sp
        var_name = detect_variable(eq_str)
        var_symbol = sp.symbols(var_name)
        rel = parse_relation(eq_str, var_symbol, None)

        if isinstance(rel, (sp.Lt, sp.Gt, sp.Le, sp.Ge)):
            sols = sp.solve_univariate_inequality(rel, var_symbol, relational=False)
        else:
            sols = sp.solveset(rel, var_symbol, domain=sp.S.Complexes)  # комплексные + триг

        return format_solution(sols, var_name)

    except ZeroDivisionError:
        return "Ошибка: деление на ноль"
    except ValueError as e:
        err = str(e).lower()
        if "logarithm" in err or "log" in err:
            return "Ошибка: аргумент логарифма ≤ 0"
        if "sqrt" in err and "negative" in err:
            return "Ошибка: квадратный корень из отрицательного числа (в комплексных числах используйте уравнение)"
        return f"Ошибка: {e}"
    except Exception as e:
        return f"Ошибка: {e}"


def solve_system(eqs: list[str], x, y) -> str:
    try:
        import sympy as sp
        x = sp.symbols('x', real=True)
        y = sp.symbols('y', real=True)
        relations = [parse_relation(eq, x, y) for eq in eqs]
        sols = sp.solve(relations, (x, y), dict=True)
        if not sols:
            return "Нет решений"
        return "\n".join(f"({nice_float(s[x])}, {nice_float(s[y])})" for s in sols[:6])
    except Exception as e:
        return f"Ошибка системы: {e}"


def analyze_function(eq_str: str, x) -> str:
    try:
        import sympy as sp
        if '=' in eq_str:
            l, r = eq_str.split('=', 1)
            left_str = l.strip()
            right_str = r.strip()
            if left_str in ('y', 'f(x)'):
                f = parse_math_expr(right_str, x)
            else:
                f = parse_math_expr(left_str, x) - parse_math_expr(right_str, x)
        else:
            f = parse_math_expr(eq_str, x)
        df = sp.diff(f, x)
        integ = sp.integrate(f, x)
        crit = sp.solve(df, x)
        extrema = []
        for cp in crit:
            d2 = sp.diff(df, x).subs(x, cp)
            if d2.is_number:
                val = float(d2)
                if val > 0: extrema.append(f"Мин в x={nice_float(cp)}")
                elif val < 0: extrema.append(f"Макс в x={nice_float(cp)}")
                else: extrema.append(f"Перегиб в x={nice_float(cp)}")
        text = f"Производная: {df}\nИнтеграл: {integ} + C\n"
        text += "Экстремумы:\n" + "\n".join(extrema) if extrema else "Нет критических точек"
        return text
    except Exception as e:
        return f"Ошибка анализа: {e}"