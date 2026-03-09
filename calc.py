import tkinter as tk
from tkinter import messagebox, Toplevel
from matplotlib import pyplot as plt
import sympy as sp
from sympy import sympify, solve, Eq, symbols, pi, E, Lt, Gt, Le, Ge, I, integrate, limit, cot, tan, Abs, factorial
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.backends._backend_tk import NavigationToolbar2Tk
import numpy as np
from sympy.core.relational import Relational
from matplotlib.lines import Line2D
from sympy.parsing.sympy_parser import parse_expr, standard_transformations, implicit_multiplication_application
import re

# Функция для красивого вывода чисел без лишних нулей
def nice_float_real(f):
    try: 
        f = float(f)
        if f.is_integer():
            return str(int(f))
        else:
            s = f"{f:.10g}"
            return s.rstrip('0').rstrip('.') if '.' in s else s
    except (TypeError, ValueError):
        return str(f)

def nice_float(x):
    if not (hasattr(x, 'is_number') and x.is_number):
        return str(x)
    try:
        x = sp.N(x, 12)
        real_part = float(sp.re(x)) # type: ignore
        imag_part = float(sp.im(x)) # type: ignore
        if imag_part == 0:
            return nice_float_real(real_part)
        if real_part == 0:
            imag_str = nice_float_real(abs(imag_part))
            return imag_str + 'i' if imag_part >= 0 else '-' + imag_str + 'i'
        real_str = nice_float_real(real_part)
        imag_str = nice_float_real(abs(imag_part))
        sign = ' + ' if imag_part > 0 else ' - '
        return real_str + sign + imag_str + 'i'
    except (TypeError, ValueError):
        return str(x)


class SmartCalculator(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Умный калькулятор | Уравнения | Системы | Графики")
        self.geometry("900x530")
        self.configure(bg="#1e293b")
        self.resizable(True, True)

        self.x, self.y = symbols('x y')
        self.equation_entries = []

        # === Левая часть: калькулятор ===
        left_frame = tk.Frame(self, bg="#1e293b", highlightbackground="#334155", highlightthickness=2)
        left_frame.pack(side="left", fill="both", expand=True, padx=10, pady=15)

        self.display = tk.Entry(left_frame, font=("Consolas", 20), justify="right",
                                bg="#0f172a", fg="#e2e8f0", insertbackground="white", bd=0, relief="flat")
        self.display.pack(fill="x", padx=20, pady=(25, 15), ipady=14)

        btn_frame = tk.Frame(left_frame, bg="#1e293b")
        btn_frame.pack(pady=5)

        buttons = [
            'C', '⌫', '(', ')', 'sin', 'cos',
            'abs', '!', '∫', 'lim', 'tan', 'ctg',
            'ln', 'log', 'lg', '×10^', 'e', 'π',
            '7', '8', '9', '+', '√', '^',
            '4', '5', '6', '-', '=', 'i',
            '1', '2', '3', '×', '<=', '>=',
            '0', '.', 'x', '÷', '<', '>'
        ]

        for i, text in enumerate(buttons):
            r, c = divmod(i, 6)
            bg_color = "#475569"
            if text in "C⌫=()": bg_color = "#334155"
            elif text in "+-×÷": bg_color = "#3b82f6"
            elif text in ['sin', 'cos', 'tan', 'ctg', 'π', 'e']: bg_color = "#8b5cf6"
            elif text in ['ln', 'log', 'lg']: bg_color = "#f97316"
            elif text in "! abs ∫ lim ×10^".split(): bg_color = "#ec4899"
            elif text in "< > <= >=".split(): bg_color = "#334155"

            btn = tk.Button(btn_frame, text=text, font=("Arial", 13, "bold"), width=6, height=2,
                            bg=bg_color, fg="white", relief="flat", bd=0,
                            command=lambda t=text: self.calc_btn(t))
            btn.grid(row=r, column=c, padx=3, pady=3)

        # Сразу фокус на поле ввода и Enter = "="
        self.display.focus_set()
        self.display.bind("<Return>", lambda e: self.evaluate_expression())
        # === Правая часть: уравнения ===
        right_frame = tk.Frame(self, bg="#1e293b", highlightbackground="#334155", highlightthickness=2)
        right_frame.pack(side="right", fill="both", expand=True, padx=10, pady=15)
        header_frame = tk.Frame(right_frame, bg="#1e293b")
        header_frame.pack(pady=(18, 10))

        tk.Label(header_frame, text="Решение уравнений и систем", font=("Arial", 16, "bold"),
                 bg="#1e293b", fg="#60a5fa").pack(side="left", padx=(40, 10))

        help_btn = tk.Button(header_frame, text="?", font=("Arial", 16, "bold"), width=2, height=1,
                             bg="#233045", fg="white", relief="flat",
                             command=self.show_instructions)
        help_btn.pack(side="left")

        action_frame = tk.Frame(right_frame, bg="#1e293b")
        action_frame.pack(pady=8)
        tk.Button(action_frame, text="Решить уравнение \n или неравенство", font=("Arial", 11, "bold"), width=16, height=2,
                  bg="#3b82f6", fg="white", command=self.solve_single).pack(side="left", padx=3)
        tk.Button(action_frame, text="Решить \n систему", font=("Arial", 11, "bold"), width=8, height=2,
                  bg="#8b5cf6", fg="white", command=self.solve_system).pack(side="left", padx=3)
        tk.Button(action_frame, text="График", font=("Arial", 11, "bold"), width=8, height=2,
                  bg="#f97316", fg="white", command=self.plot_graph).pack(side="left", padx=3)
        tk.Button(action_frame, text="Анализ \n функции", font=("Arial", 11, "bold"), width=8, height=2,
                  bg="#ec4899", fg="white", command=self.analyze_function).pack(side="left", padx=3)
        
        # Новое окошко под кнопкой "График"
        graph_options_frame = tk.Frame(right_frame, bg="#1e293b")
        graph_options_frame.pack(pady=5)
        
        tk.Label(graph_options_frame, text="X min:", bg="#1e293b", fg="#e2e8f0").grid(row=0, column=0, padx=2)
        self.x_min_entry = tk.Entry(graph_options_frame, width=5, bg="#334155", fg="#e2e8f0")
        self.x_min_entry.insert(0, "-10")
        self.x_min_entry.grid(row=0, column=1, padx=2)
        
        tk.Label(graph_options_frame, text="X max:", bg="#1e293b", fg="#e2e8f0").grid(row=0, column=2, padx=2)
        self.x_max_entry = tk.Entry(graph_options_frame, width=5, bg="#334155", fg="#e2e8f0")
        self.x_max_entry.insert(0, "10")
        self.x_max_entry.grid(row=0, column=3, padx=2)
        
        tk.Label(graph_options_frame, text="Y min:", bg="#1e293b", fg="#e2e8f0").grid(row=1, column=0, padx=2)
        self.y_min_entry = tk.Entry(graph_options_frame, width=5, bg="#334155", fg="#e2e8f0")
        self.y_min_entry.insert(0, "-10")
        self.y_min_entry.grid(row=1, column=1, padx=2)
        
        tk.Label(graph_options_frame, text="Y max:", bg="#1e293b", fg="#e2e8f0").grid(row=1, column=2, padx=2)
        self.y_max_entry = tk.Entry(graph_options_frame, width=5, bg="#334155", fg="#e2e8f0")
        self.y_max_entry.insert(0, "10")
        self.y_max_entry.grid(row=1, column=3, padx=2)
        
        tk.Label(graph_options_frame, text="Точек:", bg="#1e293b", fg="#e2e8f0").grid(row=0, column=4, padx=2)
        self.num_points_entry = tk.Entry(graph_options_frame, width=6, bg="#334155", fg="#e2e8f0")
        self.num_points_entry.insert(0, "1000")
        self.num_points_entry.grid(row=0, column=5, padx=2)

        bottom_panel = tk.Frame(right_frame, bg="#1e293b")
        bottom_panel.pack(fill="x", pady=12, padx=25)
        tk.Button(bottom_panel, text="+", font=("Arial", 22, "bold"), width=3, height=1,
                  bg="#10b981", fg="white", relief="raised",
                  command=self.add_equation_field).pack(side="left")
        self.result_text = tk.Text(bottom_panel, height=4, wrap="word", font=("Consolas", 12), bg="#1e293b", fg="#94f9a0", bd=0)
        self.result_text.pack(side="left", fill="x", expand=True, padx=(15, 0))
        scrollbar = tk.Scrollbar(bottom_panel, orient="vertical", command=self.result_text.yview, bg="#334155")
        scrollbar.pack(side="right", fill="y")
        self.result_text.config(yscrollcommand=scrollbar.set)
        self.result_text.insert("1.0", "Готов к вычислениям")
        self.eq_container = tk.Frame(right_frame, bg="#1e293b")
        self.eq_container.pack(fill="both", expand=True, padx=25)

        self.add_equation_field()

    # === Калькулятор ===
    def calc_btn(self, char):
        focused = self.focus_get()
        if not isinstance(focused, tk.Entry):
            focused = self.display
        if char == 'C':
            focused.delete(0, tk.END)
        elif char == '⌫':
            current_pos = focused.index(tk.INSERT)
            if current_pos > 0:
                focused.delete(current_pos - 1)
        else:
            if char == '=' and focused == self.display:
                self.evaluate_expression()
            else:
                to_insert = {
                    'π': "π",
                    '√': "√(",
                    '^': "^",
                    'sin': "sin(",
                    'cos': "cos(",
                    'ln': "ln(",
                    'log': "log(",
                    'e': "e",
                    'abs': "abs(",
                    '<=': "<=",
                    '>=': ">=",
                    'tan': "tan(",
                    'ctg': "ctg(",
                    'lg': "lg(",
                    'i': "i",
                    '∫': "∫(",
                    'lim': "lim(",
                    '·': "*",
                }.get(char, char)
                focused.insert(tk.INSERT, str(to_insert))
    
    def evaluate_expression(self):
        expr = self.display.get().replace('×', '*').replace('÷', '/').replace("^", "**").replace('√', 'sqrt').replace('∫', 'integrate')
        expr = re.sub(r'\|([^|]*)\|', r'Abs(\1)', expr)
        expr = re.sub(r'([^\s(]+)!', r'factorial(\1)', expr)
        try:
            ops = ['<=', '>=', '==', '=', '<', '>']
            found_op = None
            for op in sorted(ops, key=len, reverse=True):  # Split on longest first
                if op in expr:
                    found_op = op
                    parts = expr.split(op, 1)
                    break
            if found_op:
                if len(parts) != 2:
                    raise ValueError("Неверный формат неравенства. Используйте формат: выражение <отношение> выражение, например x^2 > 4")
                l_str = parts[0].strip()
                r_str = parts[1].strip()
                l = parse_expr(l_str, local_dict=self.get_sympy_locals(), transformations=standard_transformations + (implicit_multiplication_application,)) # type: ignore
                r = parse_expr(r_str, local_dict=self.get_sympy_locals(), transformations=standard_transformations + (implicit_multiplication_application,)) # type: ignore
                if found_op == '<':
                    ineq = Lt(l, r)
                elif found_op == '>':
                    ineq = Gt(l, r)
                elif found_op == '<=':
                    ineq = Le(l, r)
                elif found_op == '>=':
                    ineq = Ge(l, r)
                elif found_op in ['=', '==']:
                    ineq = Eq(l, r)
                sols = solve(ineq, self.x)
                self.display.delete(0, tk.END)
                self.display.insert(0, str(sols))
                return
            result = parse_expr(expr, local_dict=self.get_sympy_locals(), transformations=standard_transformations + (implicit_multiplication_application,)) # type: ignore
            if isinstance(result, Relational):
                result_str = "True" if result else "False"
                self.display.delete(0, tk.END)
                self.display.insert(0, result_str)
            else:
                result_str = nice_float(result) if hasattr(result, 'is_number') and result.is_number else str(result)
                self.display.delete(0, tk.END)
                self.display.insert(0, result_str)
        except ZeroDivisionError:
            messagebox.showerror("Ошибка", "Деление на ноль или математическая неопределённость.")
        except sp.SympifyError:
            messagebox.showerror("Ошибка", "Неверный синтаксис. Проверьте скобки, операторы и функции.")
        except ValueError:
            messagebox.showerror("Ошибка", "Неверный ввод. Проверьте формат выражения или параметры функций.")
        except SyntaxError:
            messagebox.showerror("Ошибка", "Синтаксическая ошибка. Убедитесь в правильности ввода.")
        except NameError:
            messagebox.showerror("Ошибка", "Неизвестная функция или переменная. Проверьте spelling.")
        except Exception as e:
            messagebox.showerror("Ошибка", "Произошла ошибка при вычислении. Проверьте ввод на корректность.")

    def get_sympy_locals(self):
        return {
            "π": pi,
            "pi" : pi,
            "e": E,
            "I": I,
            "i" : I,
            "x": self.x,
            "y": self.y,
            "integrate": lambda a, b, f: integrate(f, (self.x, a, b)),
            "lim": lambda a, b, f: limit(f, self.x, a, b if b in ['+', '-'] else '+'),
            "Abs": Abs,
            "factorial": factorial,
            "ctg": cot,
            "tan": tan,
            "log": sp.log,
            "lg": lambda x: sp.log(x, 10),
            "ln": lambda x: sp.log(x, E)
        }

    def add_equation_field(self):
        if len(self.equation_entries) >= 4:
            messagebox.showinfo("Лимит", "Максимум 4 уравнения")
            return
        frame = tk.Frame(self.eq_container, bg="#1e293b")
        frame.pack(fill="x", pady=5)
        entry = tk.Entry(frame, font=("Consolas", 14), bg="#334155", fg="#e2e8f0",
                         insertbackground="white", relief="flat", bd=8)
        entry.pack(side="left", fill="x", expand=True)
        entry.insert(0, "x + y = 5" if not self.equation_entries else "")
        remove_btn = tk.Button(frame, text="×", font=("Arial", 12, "bold"), width=3, height=1,
                               bg="#ef4444", fg="white", relief="flat",
                               command=lambda: self.remove_field(frame))
        remove_btn.pack(side="right", padx=5)
        self.equation_entries.append(entry)

    def remove_field(self, frame):
        if len(self.equation_entries) <= 1: return
        for child in frame.winfo_children():
            if isinstance(child, tk.Entry):
                self.equation_entries.remove(child)
        frame.destroy()

    def get_equations(self):
        return [e.get().strip().replace('×', '*').replace('÷', '/').replace("^", "**").replace('√', 'sqrt').replace('∫', 'integrate') for e in self.equation_entries if e.get().strip()]

    def parse_relation(self, eq_str, vars):
        ops = ['<=', '>=', '<', '>', '=']
        found_op = None
        for op in sorted(ops, key=len, reverse=True):
            if op in eq_str:
                found_op = op
                parts = eq_str.split(op, 1)
                break
        if not found_op:
            raise ValueError("Нет знака отношения. Используйте <, >, <=, >= или =.")
        try:
            locals_dict = self.get_sympy_locals()
            l = sympify(parts[0].strip(), locals=locals_dict)
            r = sympify(parts[1].strip(), locals=locals_dict)
        except sp.SympifyError:
            raise ValueError("Ошибка в выражении.")
        if found_op == '<':
            return Lt(l, r, evaluate=False), found_op
        elif found_op == '>':
            return Gt(l, r, evaluate=False), found_op
        elif found_op == '<=':
            return Le(l, r, evaluate=False), found_op
        elif found_op == '>=':
            return Ge(l, r, evaluate=False), found_op
        elif found_op == '=':
            return Eq(l, r, evaluate=False), found_op
    
    def solve_single(self):
        eqs = self.get_equations()
        if not eqs:
            self.result_text.delete('1.0', tk.END)
            self.result_text.insert('1.0', "Введите уравнение")
            self.result_text.config(fg="#ff6b6b")
            return
        try:
            rel, _ = self.parse_relation(eqs[0], self.x)  # type: ignore
            sols = solve(rel, self.x)
            if not sols:
                self.result_text.delete('1.0', tk.END)
                self.result_text.insert('1.0', "Нет решений")
                self.result_text.config(fg="#ff6b6b")
            else:
                text = "x = " + ", ".join(nice_float(s) for s in sols)
                self.result_text.delete('1.0', tk.END)
                self.result_text.insert('1.0', text)
                self.result_text.config(fg="#94f9a0")
        except ZeroDivisionError:
            self.result_text.delete('1.0', tk.END)
            self.result_text.insert('1.0', "Математическая неопределённость (деление на 0)")
            self.result_text.config(fg="#ff6b6b")
        except ValueError as ve:
            self.result_text.delete('1.0', tk.END)
            self.result_text.insert('1.0', f"Ошибка: {ve}")
            self.result_text.config(fg="#ff6b6b")
        except Exception as e:
            self.result_text.delete('1.0', tk.END)
            self.result_text.insert('1.0', "Произошла ошибка. Проверьте формат: выражение <отношение> выражение.")
            self.result_text.config(fg="#ff6b6b")

    def solve_system(self):
        eqs = self.get_equations()
        if len(eqs) < 2:
            messagebox.showwarning("Ошибка", "Нужно минимум 2 уравнения")
            return
        try:
            relations = [self.parse_relation(eq, (self.x, self.y))[0] for eq in eqs] # type: ignore
            sols = solve(relations, (self.x, self.y), dict=True)
            if not sols:
                self.result_text.delete('1.0', tk.END)
                self.result_text.insert('1.0', "Нет решений")
                self.result_text.config(fg="#ff6b6b")
            else:
                text = "\n".join(f"({nice_float(s[self.x])}, {nice_float(s[self.y])})" for s in sols[:6])
                if len(sols) > 6: text += "\n..."
                self.result_text.delete('1.0', tk.END)
                self.result_text.insert('1.0', text)
                self.result_text.config(fg="#94f9a0")
        except ZeroDivisionError:
            self.result_text.delete('1.0', tk.END)
            self.result_text.insert('1.0', "Математическая неопределённость (деление на 0)")
            self.result_text.config(fg="#ff6b6b")
        except ValueError as ve:
            self.result_text.delete('1.0', tk.END)
            self.result_text.insert('1.0', f"Ошибка: {ve}")
            self.result_text.config(fg="#ff6b6b")
        except Exception as e:
            self.result_text.delete('1.0', tk.END)
            self.result_text.insert('1.0', "Произошла ошибка. Убедитесь, что все уравнения имеют отношение и переменные x, y.")
            self.result_text.config(fg="#ff6b6b")
    
    def analyze_function(self):
        eqs = self.get_equations()
        if not eqs or len(eqs) > 1:
            messagebox.showwarning("Ошибка", "Введите ровно одну функцию f(x) или y = f(x)")
            return
        try:
            eq = eqs[0]
            locals_dict = self.get_sympy_locals()
            if '=' in eq:
                l, r = eq.split('=', 1)
                l = l.strip()
                r = r.strip()
                if l == 'y':
                    f = sympify(r, locals=locals_dict)
                elif l == 'f(x)':
                    f = sympify(r, locals=locals_dict)
                else:
                    f = sympify(l, locals=locals_dict) - sympify(r, locals=locals_dict)
            else:
                f = sympify(eq, locals=locals_dict)
            df = sp.diff(f, self.x)
            integ = sp.integrate(f, self.x)
            crit_points = solve(df, self.x)
            extrema = []
            for cp in crit_points:
                try:
                    d2 = sp.diff(df, self.x).subs(self.x, cp)
                    if d2.is_number:
                        d2_val = d2.evalf() # type: ignore
                        if d2_val > 0: # type: ignore
                            extrema.append(f"Мин в x={nice_float(cp)}: y={nice_float(f.subs(self.x, cp))}")
                        elif d2_val < 0: # type: ignore
                            extrema.append(f"Макс в x={nice_float(cp)}: y={nice_float(f.subs(self.x, cp))}")
                        else:
                            extrema.append(f"Перегиб в x={nice_float(cp)}")
                    else:
                        extrema.append(f"Крит. точка в x={nice_float(cp)}")
                except ZeroDivisionError:
                    extrema.append(f"Неопределённость в x={nice_float(cp)}")
                except Exception:
                    extrema.append(f"Крит. точка в x={nice_float(cp)}")
            text = f"Произв: {df}\nИнт: {integ} + C\n"
            if extrema:
                text += "Экстр:\n" + "\n".join(extrema)
            else:
                text += "Нет крит. точек"
            self.result_text.delete('1.0', tk.END)
            self.result_text.insert('1.0', text)
            self.result_text.config(fg="#94f9a0")
        except ZeroDivisionError:
            self.result_text.delete('1.0', tk.END)
            self.result_text.insert('1.0', "Математическая неопределённость в анализе")
            self.result_text.config(fg="#ff6b6b")
        except ValueError:
            self.result_text.delete('1.0', tk.END)
            self.result_text.insert('1.0', "Неверный ввод. Проверьте формат функции.")
            self.result_text.config(fg="#ff6b6b")
        except Exception as e:
            self.result_text.delete('1.0', tk.END)
            self.result_text.insert('1.0', "Ошибка анализа. Убедитесь, что функция зависит только от x.")
            self.result_text.config(fg="#ff6b6b")
    
    # === ИНТЕРАКТИВНЫЙ ГРАФИК ===
    def plot_graph(self):
        eqs = self.get_equations()
        if not eqs: 
            messagebox.showerror("Ошибка", "Введите хотя бы одно уравнение или неравенство.")
            return

        # Проверка
        for eq_str in eqs:
            ops = ['<=', '>=', '<', '>', '=']
            if not any(op in eq_str for op in ops):
                messagebox.showerror("Ошибка", f"В уравнении '{eq_str}' нет знака отношения. Используйте <, >, <=, >= или =.")
                return
            try:
                parts = eq_str.split(next(op for op in ops if op in eq_str), 1)
                locals_dict = self.get_sympy_locals()
                sympify(parts[0].strip(), locals=locals_dict)
                sympify(parts[1].strip(), locals=locals_dict)
            except Exception as e:
                messagebox.showerror("Ошибка", f"Неверный формат в '{eq_str}'. Проверьте синтаксис.")
                return
        try:
            x_min = float(self.x_min_entry.get())
            x_max = float(self.x_max_entry.get())
            y_min = float(self.y_min_entry.get())
            y_max = float(self.y_max_entry.get())
            num_points = min(int(self.num_points_entry.get()), 10000)
            if x_min >= x_max or y_min >= y_max or num_points <= 0:
                raise ValueError("Неверные пределы или количество точек.")
        except ValueError:
            messagebox.showerror("Ошибка", f"Неверные параметры графика. Используйте числа, x_min < x_max и т.д.")
            return

        win = Toplevel(self)
        win.title("График — зум, перемещение, сохранение")
        win.geometry("920x720")
        win.configure(bg="#1e293b")
        fig = plt.figure(figsize=(11, 8), dpi=100, facecolor="#1e293b")
        fig.subplots_adjust(left=0.043, bottom=0.033, right=0.998, top=0.993)
        ax = fig.add_subplot(111)
        ax.set_facecolor("#0f172a")
        ax.grid(True, alpha=0.4, color="#475569")
        ax.axhline(0, color='white', lw=1.2, alpha=0.8)
        ax.axvline(0, color='white', lw=1.2, alpha=0.8)
        ax.tick_params(colors="white")
        ax.set_xlabel("x", color="white", fontsize=12)
        ax.set_ylabel("y", color="white", fontsize=12)

        colors = ["#60a5fa", "#f59e0b", "#10b981", "#ef4444"]

        try:
            x_range = np.linspace(x_min, x_max, num_points)
            y_range = np.linspace(y_min, y_max, num_points)
            X, Y = np.meshgrid(x_range, y_range)

            locals_dict = self.get_sympy_locals()
            for i, eq_str in enumerate(eqs):
                ops = ['<=', '>=', '<', '>', '=']
                found_op = None
                for op in sorted(ops, key=len, reverse=True):
                    if op in eq_str:
                        found_op = op
                        parts = eq_str.split(op, 1)
                        break
                if not found_op:
                    raise ValueError("Нет знака отношения в " + eq_str)
                l = sympify(parts[0].strip(), locals=locals_dict)
                r = sympify(parts[1].strip(), locals=locals_dict)
                expr = l - r
                f = sp.lambdify((self.x, self.y), expr, "numpy")
                Z = f(X, Y)
                if np.any(np.isnan(Z)) or np.any(np.isinf(Z)):
                    messagebox.showwarning("Предупреждение", f"В уравнении {i+1} есть математические неопределённости (NaN или Inf).")
                if found_op == '=':
                    cs = ax.contour(X, Y, Z, levels=[0], colors=colors[i], linewidths=2.8)
                    # Убрано clabel
                else:
                    # Граница
                    ax.contour(X, Y, Z, levels=[0], colors=colors[i], linewidths=1.5, linestyles='dashed')
                    # Заливка
                    fill_color = colors[i]
                    alpha = 0.3
                    if found_op in ['>', '>=']:
                        ax.contourf(X, Y, Z, levels=[0, np.nanmax(Z) + 1], colors=[(0,0,0,0), fill_color], alpha=alpha)
                    elif found_op in ['<', '<=']:
                        ax.contourf(X, Y, Z, levels=[np.nanmin(Z) - 1, 0], colors=[fill_color, (0,0,0,0)], alpha=alpha)
                    # Метка для неравенства
                    ax.text(0.05, 0.95 - i*0.05, eq_str, transform=ax.transAxes, fontsize=9, color=colors[i], va='top')

            # Легенда с цветными линиями
            handles = [Line2D([0], [0], color=colors[i], lw=2, label=eq_str) for i, eq_str in enumerate(eqs)]
            ax.legend(handles=handles, facecolor="#1e293b", labelcolor="white", loc="upper right")

            # Установка лимитов
            ax.set_xlim(x_min, x_max)
            ax.set_ylim(y_min, y_max)

            canvas = FigureCanvasTkAgg(fig, master=win)
            canvas.draw()
            toolbar = NavigationToolbar2Tk(canvas, win)
            toolbar.update()
            toolbar['background'] = "#334155"
            for child in toolbar.winfo_children():
                try:
                    child['background'] = "#334155"
                except:
                    pass
                try:
                    child['foreground'] = "#D8D8D8"
                except:
                    pass

            canvas.get_tk_widget().pack(side="top", fill="both", expand=True, padx=12, pady=12)
            toolbar.pack(side="bottom", fill="x", padx=10)

        except ZeroDivisionError:
            messagebox.showerror("Ошибка графика", "Математическая неопределённость (деление на 0).")
            win.destroy()
        except ValueError:
            messagebox.showerror("Ошибка графика", "Неверный ввод. Проверьте выражения.")
            win.destroy()
        except Exception as e:
            messagebox.showerror("Ошибка графика", "Произошла ошибка. Проверьте, что уравнения зависят от x и/или y, и синтаксис правильный.")
            win.destroy()

    def show_instructions(self):
        instr_win = Toplevel(self)
        instr_win.title("Инструкция")
        instr_win.geometry("600x400")
        instr_win.configure(bg="#1e293b")

        text = tk.Text(instr_win, bg="#0f172a", fg="#e2e8f0", padx=10, font=("Consolas", 12), wrap="word")
        text.pack(fill="both", expand=True, padx=10, pady=10)

        instructions = """
Документация:

Базовый калькулятор

- C — полностью очищает поле ввода.

- ⌫ — удаляет один символ слева от курсора в активном поле ввода. 

- ( и ) — круглые скобки (изменяют порядок операций по правилам математики).  

- sin — функция синуса: sin(а) принимает значения в радианах. Возвращает синус угла а.

- cos — функция косинуса: cos(а) принимает значения в радианах. Возвращает косинус угла а.  

- π — константа π (3,14159…).  

- ^ — возведение в степень (либо **).  

- √ — корень квадратный: sqrt(a) возвращает квадратный корень числа а.

- ln — натуральный логарифм: ln(a) возвращает значение натурального логарифма числа a.  

- log — логарифм log(а, b) возвращает значение логарифма a по основанию b.  

- e — основание натуральных логарифмов Е (2,71828…).  

- ! — факториал целого неотрицательного числа.  

- < > ≤ ≥ — вставляют соответствующие знаки отношения для решения неравенств.  

- abs — функция модуля: abs(а) возвращает модуль числа a. Также поддерживается |a|.

- exp — функция экспоненты: exp(а) возвращает число Е в степени а.

- = — выражение в поле ввода калькулятора (или решает неравенство с переменной x).

- Цифры 0–9 и точка . — ввод числовых значений и десятичной дроби.

- + − × ÷ — базовые арифметические операции (сложение, вычитание, умножение, деление).

- x — вставляет переменной x (используется в уравнениях и при обычных вычислениях).

- tan — тангенс: tan(a).

- ctg — котангенс: ctg(a).

- lg — десятичный логарифм: lg(a).

- i — мнимая единица: I.

- ∫ — определённый интеграл: integrate(a, b, f) где a - нижний предел, b - верхний предел, f - сама функция.

- lim — лимит: lim(a, b, f) где a - нижний предел, b - верхний предел, f - сама функция.

Элементы управления калькулятора анализа:

- Решить уравнение или неравенство — решает одно уравнение/неравенство с переменной x (поддерживает =, <, >, ≤, ≥).  

- Решить систему — решает систему из 2–4 уравнений/неравенств с переменными x и y, выводит до 6 решений. 

- График — строит интерактивный график всех введённых уравнений (= — линия) и неравенств (заливка области решений). 

- Анализ функции — для одной функции вида y = f(x) или f(x) вычисляет производную, первообразную и находит локальные экстремумы/перегибы.  

- + (зелёная кнопка) — добавляет новое поле для ввода уравнения/неравенства (максимум 4).  

- × (красная кнопка в строке) — удаляет соответствующее поле уравнения (оставляет минимум одно).  

- ? — открывает окно с полной инструкцией по использованию калькулятора.  


Параметры графика:

- X min / X max — левый и правый пределы по оси абсцисс (по умолчанию –10 и 10).
- Y min / Y max — нижний и верхний пределы по оси ординат (по умолчанию –10 и 10).  

- N Точек — количество точек расчёта сетки (по умолчанию 1000, максимум 10 000; Скорость постоения обратнопропорциональна количеству точек).
        """

        text.insert(tk.END, instructions)
        text.config(state="disabled")


if __name__ == "__main__":
    app = SmartCalculator()
    app.mainloop()