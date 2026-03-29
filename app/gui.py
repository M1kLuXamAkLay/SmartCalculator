import tkinter as tk
from tkinter import messagebox, Toplevel, ttk, filedialog
import re
import traceback
import os
import configparser
import queue
import threading
import time

from utils import nice_float, get_sympy_locals, format_solution, detect_variable, preprocess_expr
from ai_methods import recognize_from_photo, solve_with_ai


class SmartCalculator(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Умный калькулятор | ЕГЭ профильная математика")
        self.geometry("1280x520")
        self.configure(bg="#1e293b")
        self.resizable(True, True)

        self.equation_entries = []
        self.config = self._load_config()
        self._setup_paths()

        self.computing_start = None
        self.stop_ai_event = threading.Event()
        self.ai_running = False
        self.pending_stop = False
        self.ai_result_queue = queue.Queue()
        self.showing_warning = False
        self.ai_progress_logs = []

        self._create_left_panel()
        self._create_right_panel()

    def _load_config(self):
        config = configparser.ConfigParser()
        config_path = "config.txt"
        if os.path.exists(config_path):
            config.read(config_path)

        updated = False

        if not config.has_section('AI'):
            config['AI'] = {'model': 'qwen2.5:7b', 'temperature': '0.3'}
            updated = True

        if not config.has_section('GRAPH'):
            config['GRAPH'] = {'x_min': '-50', 'x_max': '50', 'y_min': '-50', 'y_max': '50', 'points': '1500'}
            updated = True

        # ===================== ИСПРАВЛЕННАЯ ЛОГИКА ПУТЕЙ =====================
        user_home = os.path.expanduser("~")
        default_ollama_models = os.path.join(user_home, ".ollama", "models")
        default_matplotlib = os.path.join(user_home, ".matplotlib")

        if not config.has_section('PATHS'):
            config['PATHS'] = {
                'ollama_models': default_ollama_models,
                'matplotlib_config': default_matplotlib
            }
            updated = True
        else:
            # Если в config.txt старый/неправильный путь — принудительно исправляем
            current_ollama = config.get('PATHS', 'ollama_models', fallback='')
            current_mpl = config.get('PATHS', 'matplotlib_config', fallback='')
            if current_ollama != default_ollama_models or current_mpl != default_matplotlib:
                config['PATHS']['ollama_models'] = default_ollama_models
                config['PATHS']['matplotlib_config'] = default_matplotlib
                updated = True

        if updated or not os.path.exists(config_path):
            with open(config_path, 'w', encoding='utf-8') as f:
                config.write(f)

        return config

    def _setup_paths(self):
        try:
            ollama_models = self.config.get('PATHS', 'ollama_models')
            if ollama_models:
                os.makedirs(ollama_models, exist_ok=True)
                os.environ['OLLAMA_MODELS'] = ollama_models   # <-- теперь всегда правильный путь

            mpl_config = self.config.get('PATHS', 'matplotlib_config')
            if mpl_config:
                os.makedirs(mpl_config, exist_ok=True)
                os.environ['MPLCONFIGDIR'] = mpl_config
        except Exception as e:
            print(f"[WARNING] Не удалось создать папки: {e}")

    # ===================== ЛЕВАЯ ЧАСТЬ =====================
    def _create_left_panel(self):
        left_frame = tk.Frame(self, bg="#1e293b", highlightbackground="#334155", highlightthickness=2)
        left_frame.pack(side="left", fill="both", expand=True, padx=10, pady=15)

        self.display = tk.Entry(left_frame, font=("Consolas", 20), justify="right", bg="#0f172a", fg="#e2e8f0", insertbackground="white", bd=0)
        self.display.pack(fill="x", padx=20, pady=(25, 15), ipady=14)

        btn_frame = tk.Frame(left_frame, bg="#1e293b")
        btn_frame.pack(pady=5)

        buttons = ['C', '⌫', '(', ')', 'sin', 'cos', '|', '!', '∫', 'lim', 'tan', 'ctg',
                   'ln', 'log', 'lg', '×10^', 'e', 'π', '7', '8', '9', '+', '√', '^',
                   '4', '5', '6', '-', '=', 'i', '1', '2', '3', '×', '<=', '>=',
                   '0', '.', 'x', '÷', '<', '>']

        for i, text in enumerate(buttons):
            r, c = divmod(i, 6)
            bg_color = "#475569"
            if text in "C⌫=()": bg_color = "#334155"
            elif text in "+-×÷": bg_color = "#3b82f6"
            elif text in ['sin', 'cos', 'tan', 'ctg', 'π', 'e']: bg_color = "#8b5cf6"
            elif text in ['ln', 'log', 'lg']: bg_color = "#f97316"
            elif text in "! | ∫ lim ×10^".split(): bg_color = "#ec4899"
            elif text in "< > <= >=".split(): bg_color = "#334155"

            btn = tk.Button(btn_frame, text=text, font=("Arial", 13, "bold"), width=6, height=2,
                            bg=bg_color, fg="white", relief="flat", bd=0,
                            command=lambda t=text: self.calc_btn(t))
            btn.grid(row=r, column=c, padx=3, pady=3)

        self.display.focus_set()
        self.display.bind("<Return>", lambda e: self.evaluate_expression())

    def calc_btn(self, char):
        focused = self.focus_get()
        if not isinstance(focused, tk.Entry):
            focused = self.display
        if char == 'C':
            focused.delete(0, tk.END)
        elif char == '⌫':
            pos = focused.index(tk.INSERT)
            if pos > 0:
                focused.delete(pos - 1)
        else:
            if char == '=' and focused == self.display:
                self.evaluate_expression()
            else:
                to_insert = {'π': "π", '√': "√(", '^': "^", 'sin': "sin(", 'cos': "cos(",
                             'ln': "ln(", 'log': "log(", 'e': "e", 'tan': "tan(",
                             'ctg': "ctg(", 'lg': "lg(", 'i': "i", '∫': "∫(", 'lim': "lim("}.get(char, char)
                focused.insert(tk.INSERT, str(to_insert))

    def evaluate_expression(self):
        try:
            raw = self.display.get()
            var_name = detect_variable(raw)
            import sympy as sp
            from sympy.parsing.sympy_parser import parse_expr, standard_transformations, implicit_multiplication_application
            var_symbol = sp.symbols(var_name)
            expr = preprocess_expr(raw)
            result = []
            level = 0
            for char in expr:
                if char == '(': level += 1
                elif char == ')': level = max(0, level-1)
                elif char == ',' and level == 0: result.append('.'); continue
                result.append(char)
            expr = ''.join(result)

            ops = ['<=', '>=', '==', '=', '<', '>']
            found_op = None
            for op in sorted(ops, key=len, reverse=True):
                if op in expr:
                    found_op = op
                    parts = expr.split(op, 1)
                    break

            if found_op:
                l_str, r_str = parts[0].strip(), parts[1].strip()
                l = parse_expr(l_str, local_dict=get_sympy_locals(var_symbol), transformations=standard_transformations + (implicit_multiplication_application,))
                r = parse_expr(r_str, local_dict=get_sympy_locals(var_symbol), transformations=standard_transformations + (implicit_multiplication_application,))
                if found_op == '<': ineq = sp.Lt(l, r)
                elif found_op == '>': ineq = sp.Gt(l, r)
                elif found_op == '<=': ineq = sp.Le(l, r)
                elif found_op == '>=': ineq = sp.Ge(l, r)
                else: ineq = sp.Eq(l, r)
                if isinstance(ineq, (sp.Lt, sp.Gt, sp.Le, sp.Ge)):
                    sols = sp.solve_univariate_inequality(ineq, var_symbol, relational=False)
                else:
                    sols = sp.solve(ineq, var_symbol)
                result_str = format_solution(sols, var_name)
                self.display.delete(0, tk.END)
                self.display.insert(0, result_str)
                return

            result = parse_expr(expr, local_dict=get_sympy_locals(var_symbol), transformations=standard_transformations + (implicit_multiplication_application,))
            result_str = nice_float(result) if hasattr(result, 'is_number') and result.is_number else str(result)
            self.display.delete(0, tk.END)
            self.display.insert(0, result_str)
        except Exception as e:
            self.display.delete(0, tk.END)
            self.display.insert(0, "Некорректный ввод. Проверьте выражение")

    # ===================== ПРАВАЯ ЧАСТЬ =====================
    def _create_right_panel(self):
        right_frame = tk.Frame(self, bg="#1e293b", highlightbackground="#334155", highlightthickness=2)
        right_frame.pack(side="right", fill="y", expand=False, padx=10, pady=12)

        header_frame = tk.Frame(right_frame, bg="#1e293b")
        header_frame.pack(pady=(10, 8))
        tk.Label(header_frame, text="Решение уравнений и систем", font=("Arial", 16, "bold"), bg="#1e293b", fg="#60a5fa").pack(side="left", padx=(30, 10))
        help_btn = tk.Button(header_frame, text="?", font=("Arial", 16, "bold"), width=2, height=1, bg="#233045", fg="white", relief="flat", command=self.show_instructions)
        help_btn.pack(side="left")

        action_frame = tk.Frame(right_frame, bg="#1e293b")
        action_frame.pack(pady=6)
        row = [("Решить уравнение или неравенство", self._solve_single), ("Решить систему", self._solve_system),
               ("График", self._plot), ("Анализ функции", self._analyze), ("Решать по фото", self._solve_by_photo)]
        for text, cmd in row:
            ttk.Button(action_frame, text=text, command=cmd).pack(side="left", padx=4)
        tk.Frame(action_frame, height=1, bg="#334155").pack(fill="x", pady=4)

        graph_options_frame = tk.Frame(right_frame, bg="#1e293b")
        graph_options_frame.pack(pady=4)
        tk.Label(graph_options_frame, text="X min:", bg="#1e293b", fg="#e2e8f0").grid(row=0, column=0, padx=2)
        self.x_min_entry = tk.Entry(graph_options_frame, width=5, bg="#334155", fg="#e2e8f0")
        self.x_min_entry.insert(0, self.config.get('GRAPH', 'x_min', fallback='-10'))
        self.x_min_entry.grid(row=0, column=1, padx=2)
        tk.Label(graph_options_frame, text="X max:", bg="#1e293b", fg="#e2e8f0").grid(row=0, column=2, padx=2)
        self.x_max_entry = tk.Entry(graph_options_frame, width=5, bg="#334155", fg="#e2e8f0")
        self.x_max_entry.insert(0, self.config.get('GRAPH', 'x_max', fallback='10'))
        self.x_max_entry.grid(row=0, column=3, padx=2)
        tk.Label(graph_options_frame, text="Y min:", bg="#1e293b", fg="#e2e8f0").grid(row=1, column=0, padx=2)
        self.y_min_entry = tk.Entry(graph_options_frame, width=5, bg="#334155", fg="#e2e8f0")
        self.y_min_entry.insert(0, self.config.get('GRAPH', 'y_min', fallback='-10'))
        self.y_min_entry.grid(row=1, column=1, padx=2)
        tk.Label(graph_options_frame, text="Y max:", bg="#1e293b", fg="#e2e8f0").grid(row=1, column=2, padx=2)
        self.y_max_entry = tk.Entry(graph_options_frame, width=5, bg="#334155", fg="#e2e8f0")
        self.y_max_entry.insert(0, self.config.get('GRAPH', 'y_max', fallback='10'))
        self.y_max_entry.grid(row=1, column=3, padx=2)
        tk.Label(graph_options_frame, text="Точек:", bg="#1e293b", fg="#e2e8f0").grid(row=0, column=4, padx=2)
        self.num_points_entry = tk.Entry(graph_options_frame, width=6, bg="#334155", fg="#e2e8f0")
        self.num_points_entry.insert(0, self.config.get('GRAPH', 'points', fallback='1000'))
        self.num_points_entry.grid(row=0, column=5, padx=2)

        eq_control_frame = tk.Frame(right_frame, bg="#1e293b")
        eq_control_frame.pack(fill="x", padx=25, pady=(8, 2))
        ttk.Button(eq_control_frame, text="+ Добавить уравнение", command=self.add_equation_field).pack(side="left")

        self.eq_container = tk.Frame(right_frame, bg="#1e293b")
        self.eq_container.pack(fill="x", expand=False, padx=25, pady=1)
        self.add_equation_field()

        bottom_panel = tk.Frame(right_frame, bg="#1e293b")
        bottom_panel.pack(fill="both", expand=True, pady=8, padx=20)
        self.result_text = tk.Text(bottom_panel, height=8, wrap="word", font=("Consolas", 12), bg="#1e293b", fg="#94f9a0", bd=0)
        self.result_text.pack(side="left", fill="both", expand=True, padx=(15, 0))
        scrollbar = tk.Scrollbar(bottom_panel, orient="vertical", command=self.result_text.yview)
        scrollbar.pack(side="right", fill="y")
        self.result_text.config(yscrollcommand=scrollbar.set)
        self.result_text.insert("1.0", "Готов к вычислениям")
        self.result_text.config(state="disabled")

    def add_equation_field(self):
        if len(self.equation_entries) >= 4:
            self.result_text.config(state='normal')
            self.result_text.delete("1.0", tk.END)
            self.result_text.insert("1.0", "Максимум 4 уравнения")
            self.result_text.config(state='disabled')
            return
        frame = tk.Frame(self.eq_container, bg="#1e293b")
        frame.pack(fill="x", pady=5)
        entry = tk.Entry(frame, font=("Consolas", 14), bg="#334155", fg="#e2e8f0", relief="flat")
        entry.pack(side="left", fill="x", expand=True)
        entry.insert(0, "y = x + 5" if not self.equation_entries else "")
        remove_btn = ttk.Button(frame, text="×", command=lambda: self.remove_field(frame))
        remove_btn.pack(side="right", padx=5)
        self.equation_entries.append(entry)

    def remove_field(self, frame):
        if len(self.equation_entries) <= 1:
            return
        for child in frame.winfo_children():
            if isinstance(child, tk.Entry):
                self.equation_entries.remove(child)
        frame.destroy()

    def get_equations(self):
        return [e.get().strip().replace(',', '.') for e in self.equation_entries if e.get().strip()]

    def _finish_action(self, result_text: str, fg_color: str = "#94f9a0"):
        self.result_text.config(state='normal')
        self.result_text.delete("1.0", tk.END)
        self.result_text.insert("1.0", result_text)
        self.result_text.config(state='disabled')
        self.result_text.config(fg=fg_color)
        self.ai_running = False
        self.pending_stop = False
        self.showing_warning = False
        self.ai_progress_logs.clear()

    def _handle_ai_interrupt(self):
        if not self.ai_running:
            return True
        if self.pending_stop:
            self.stop_ai_event.set()
            self.pending_stop = False
            self.showing_warning = False
            return True
        else:
            self.pending_stop = True
            self.showing_warning = True
            return False

    def _run_compute(self, compute_func):
        try:
            result = compute_func()
            self.after(0, lambda: self._finish_action(result))
        except Exception as e:
            self.after(0, lambda: self._finish_action(f"Ошибка вычисления: {str(e)}", "#ff6b6b"))

    def _update_ai_status(self):
        if not self.ai_running:
            return

        elapsed = int(time.time() - self.computing_start)
        mins, secs = divmod(elapsed, 60)
        time_str = f"{mins:02d}:{secs:02d}"
        self.result_text.config(state='normal')
        self.result_text.delete("1.0", tk.END)

        if self.ai_progress_logs and self.ai_progress_logs[-1].startswith("📥"):
            # Режим скачивания модели — как было раньше
            warning = "⚠️ ВНИМАНИЕ: НЕ ЗАКРЫВАЙТЕ ПРОГРАММУ во время скачивания модели!"
            self.result_text.insert("1.0", warning + "\n")
            self.result_text.insert(tk.END, self.ai_progress_logs[-1] + "\n")
        else:
            # === ОСНОВНОЙ РЕЖИМ РЕШЕНИЯ ЗАДАЧИ ===
            self.result_text.insert("1.0", "📝 Распознана задача ЕГЭ. Решаю с помощью ИИ...\n")
            if self.ai_progress_logs:
                self.result_text.insert(tk.END, self.ai_progress_logs[-1] + "\n")
            
            self.result_text.insert(tk.END, time_str)

        if self.showing_warning:
            self.result_text.insert(tk.END, "\n\n⚠️ Вы хотите остановить решение нейросети?\n"
                                           "Нажмите ещё раз на эту кнопку для подтверждения остановки "
                                           "и выполнения нового действия.\n")

        self.result_text.config(state='disabled')
        self.result_text.see("end")
        self.after(150, self._update_ai_status)

    def _append_progress_message(self, msg: str):
        if hasattr(self, 'ai_progress_logs'):
            if msg.startswith('📥 ') and self.ai_progress_logs and self.ai_progress_logs[-1].startswith('📥 '):
                self.ai_progress_logs[-1] = msg
            elif "Модель" in msg and ("успешно" in msg or "уже установлена" in msg or "скачана" in msg):
                self.ai_progress_logs.clear()
            else:
                self.ai_progress_logs.append(msg)

    def _check_ai_result(self):
        try:
            result = self.ai_result_queue.get_nowait()
            self.ai_running = False
            self.showing_warning = False
            self.after(0, lambda r=result: self._finish_action(r))
        except queue.Empty:
            if self.ai_running:
                self.after(200, self._check_ai_result)

    def _start_ai_processing(self, raw_text: str):
        self.ai_running = True
        self.stop_ai_event.clear()
        self.pending_stop = False
        self.showing_warning = False
        self.computing_start = time.time()
        self.ai_progress_logs.clear()

        self.result_text.config(state='normal')
        self.result_text.delete("1.0", tk.END)
        self.result_text.insert("1.0", "🔄 Проверка и запуск ИИ-модели...\n")
        self.result_text.config(state='disabled')

        self._update_ai_status()

        def progress_callback(msg: str):
            self.after(0, lambda m=msg: self._append_progress_message(m))

        def ai_worker():
            try:
                result = solve_with_ai(raw_text, progress_callback=progress_callback, stop_event=self.stop_ai_event)
                self.ai_result_queue.put(result)
            except Exception as e:
                self.ai_result_queue.put(f"Ошибка ИИ: {str(e)}")

        threading.Thread(target=ai_worker, daemon=True).start()
        self._check_ai_result()

    def _solve_by_photo(self):
        if not self._handle_ai_interrupt():
            return

        self.result_text.config(state='normal')
        self.result_text.delete("1.0", tk.END)
        self.result_text.insert("1.0", "📸 Выберите файл фото...\n")
        self.result_text.config(state='disabled')

        file = filedialog.askopenfilename(filetypes=[("Images", "*.png *.jpg *.jpeg *.webp")])
        if not file:
            self._finish_action("Файл не выбран.")
            return

        self.result_text.config(state='normal')
        self.result_text.delete("1.0", tk.END)
        self.result_text.insert("1.0", "📸 Распознаю фото...\n")
        self.result_text.config(state='disabled')

        def photo_worker():
            try:
                raw_text = recognize_from_photo(file)
                if not raw_text.strip():
                    raise ValueError("Не удалось распознать текст с фото")

                lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
                relation_ops = ['=', '<', '>', '<=', '>=']
                task_keywords = ['решить', 'найти', 'вычислить', 'сколько', 'докажите', 'построить',
                                 'доказать', 'задача', 'дано', 'требуется', 'пример', 'условие', 'ответ',
                                 'егэ', 'задание', 'найдите', 'определить']

                text_lower = raw_text.lower()
                has_relation = any(any(op in line for op in relation_ops) for line in lines)
                has_complex_func = any(func in raw_text for func in ['sqrt', 'sin', 'cos', 'tan', 'ctg', 'ln', 'log', 'lg'])
                is_complex_task = (any(kw in text_lower for kw in task_keywords) or len(raw_text) > 350 or len(lines) > 6 or
                                   (len(lines) == 1 and not has_relation) or has_complex_func)

                if has_relation and not is_complex_task and len(lines) <= 4:
                    self.after(0, lambda l=lines: self._load_equations_and_solve(l))
                    return

                self.after(0, lambda t=raw_text: self._start_ai_processing(t))
                return
            except Exception as e:
                self.after(0, lambda: self._finish_action(f"Не удалось распознать выражение.\nПроверьте качество фото.\nПодробно: {str(e)}", "#ff6b6b"))

        threading.Thread(target=photo_worker, daemon=True).start()

    def _load_equations_and_solve(self, lines: list):
        for child in self.eq_container.winfo_children():
            child.destroy()
        self.equation_entries.clear()
        for line in lines:
            self.add_equation_field()
            self.equation_entries[-1].delete(0, tk.END)
            self.equation_entries[-1].insert(0, line)

        self.result_text.config(state='normal')
        self.result_text.delete("1.0", tk.END)
        self.result_text.insert("1.0", f"✅ Загружено {len(lines)} выражени{'е' if len(lines) == 1 else 'я'}.\nАвтоматически решаю через SymPy...\n")
        self.result_text.config(state='disabled')

        if len(lines) == 1:
            self._solve_single()
        else:
            self._solve_system()

    def _solve_single(self):
        if not self._handle_ai_interrupt(): return
        eqs = self.get_equations()
        if not eqs:
            self._finish_action("Некорректный ввод. Введите хотя бы одно уравнение")
            return
        def compute():
            from algebra import solve_single
            return solve_single(eqs[0])
        threading.Thread(target=self._run_compute, args=(compute,), daemon=True).start()

    def _solve_system(self):
        if not self._handle_ai_interrupt(): return
        eqs = self.get_equations()
        if len(eqs) < 2:
            self._finish_action("Некорректный ввод. Нужно минимум 2 уравнения")
            return
        def compute():
            import sympy as sp
            x, y = sp.symbols('x y')
            from algebra import solve_system
            return solve_system(eqs, x, y)
        threading.Thread(target=self._run_compute, args=(compute,), daemon=True).start()

    def _analyze(self):
        if not self._handle_ai_interrupt(): return
        eqs = self.get_equations()
        if not eqs:
            self._finish_action("Некорректный ввод. Введите одну функцию")
            return
        def compute():
            import sympy as sp
            x = sp.symbols('x')
            from algebra import analyze_function
            return analyze_function(eqs[0], x)
        threading.Thread(target=self._run_compute, args=(compute,), daemon=True).start()

    def _plot(self):
        if not self._handle_ai_interrupt(): return
        try:
            from plotting import plot_graph
            eqs = self.get_equations()
            if not eqs:
                self._finish_action("Некорректный ввод. Введите хотя бы одно уравнение")
                return
            x_min = float(self.x_min_entry.get())
            x_max = float(self.x_max_entry.get())
            y_min = float(self.y_min_entry.get())
            y_max = float(self.y_max_entry.get())
            num_points = min(int(self.num_points_entry.get()), 10000)
            if x_min >= x_max or y_min >= y_max or num_points <= 0:
                raise ValueError("Неверные пределы графика")
            plot_graph(eqs, x_min, x_max, y_min, y_max, num_points)
        except Exception as e:
            self._finish_action("Неверные параметры графика. Проверьте числа")

    def show_instructions(self):
        instr_win = Toplevel(self)
        instr_win.title("Инструкция")
        instr_win.geometry("715x545")
        instr_win.configure(bg="#1e293b")
        text = tk.Text(instr_win, bg="#0f172a", fg="#e2e8f0", padx=10, font=("Consolas", 12), wrap="word")
        text.pack(fill="both", expand=True, padx=10, pady=10)
        instructions = """Документация:

Базовый калькулятор

- C — полностью очищает поле ввода.
- ⌫ — удаляет один символ.
- ( и ) — круглые скобки.
- sin, cos, tan, ctg — тригонометрические функции (в радианах).
- π, e — математические константы.
- ^ или ** — возведение в степень.
- √ — квадратный корень.
- ln, log, lg — логарифмы.
- ! — факториал.
- |x| — модуль числа (кнопка | ).
- < > <= >= — знаки для неравенств.
- x (или любая буква a-z) — переменная.
- i — мнимая единица.
- ∫ и lim — интеграл и предел.

Элементы управления справа:

- Решить уравнение или неравенство → выводит x ∈ [a; b] ∪ ... или x₁ = ...
- Решить систему
- График (с настраиваемыми пределами)
- Анализ функции (производная, интеграл, экстремумы)
- Решение по фото (решение задач или добавление уравнений в поля для ввода)
"""
        text.insert(tk.END, instructions)
        text.config(state="disabled")


if __name__ == "__main__":
    app = SmartCalculator()
    app.mainloop()