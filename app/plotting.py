import matplotlib
matplotlib.use('TkAgg')   # ← ДОЛЖЕН БЫТЬ САМЫМ ПЕРВЫМ ИМПОРТОМ

import numpy as np
import sympy as sp
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.backends._backend_tk import NavigationToolbar2Tk
from matplotlib.lines import Line2D
from tkinter import Toplevel
from utils import parse_math_expr


def plot_graph(eqs: list[str], x_min, x_max, y_min, y_max, num_points=1000):
    win = Toplevel()
    win.title("График — зум, перемещение, сохранение")
    win.geometry("920x720")
    win.configure(bg="#1e293b")

    fig = plt.figure(figsize=(11, 8), dpi=100, facecolor="#1e293b")
    fig.subplots_adjust(left=0.043, bottom=0.033, right=0.998, top=0.993)
    ax = fig.add_subplot(111)
    ax.set_facecolor("#0f172a")
    ax.grid(True, alpha=0.4, color="#475569")
    ax.axhline(0, color='white', lw=1.2)
    ax.axvline(0, color='white', lw=1.2)
    ax.tick_params(colors="white")
    ax.set_xlabel("x", color="white")
    ax.set_ylabel("y", color="white")

    colors = ["#60a5fa", "#f59e0b", "#10b981", "#ef4444"]
    X, Y = np.meshgrid(np.linspace(x_min, x_max, num_points), np.linspace(y_min, y_max, num_points))

    x_sym = sp.symbols('x')
    y_sym = sp.symbols('y')

    for i, eq_str_raw in enumerate(eqs):
        ops = ['<=', '>=', '<', '>', '=']
        left_str = eq_str_raw
        right_str = "0"
        op_type = '='
        for op in sorted(ops, key=len, reverse=True):
            if op in eq_str_raw:
                left_str, right_str = [s.strip() for s in eq_str_raw.split(op, 1)]
                op_type = op
                break

        try:
            l_parsed = parse_math_expr(left_str, x_sym, y_sym)
            r_parsed = parse_math_expr(right_str, x_sym, y_sym)
            expr = l_parsed - r_parsed
            f = sp.lambdify((x_sym, y_sym), expr, "numpy")
            Z = f(X, Y)
        except Exception as e:
            print(f"[PLOT ERROR] {eq_str_raw}: {e}")
            continue

        if op_type == '=':
            ax.contour(X, Y, Z, levels=[0], colors=colors[i], linewidths=2.8)
        else:
            ax.contour(X, Y, Z, levels=[0], colors=colors[i], linestyles='dashed')
            alpha = 0.3
            if op_type in ['>', '>=']:
                maxz = np.nanmax(Z) if np.any(np.isfinite(Z)) else 1
                ax.contourf(X, Y, Z, levels=[0, maxz + 1], colors=[(0, 0, 0, 0), colors[i]], alpha=alpha)
            else:
                minz = np.nanmin(Z) if np.any(np.isfinite(Z)) else -1
                ax.contourf(X, Y, Z, levels=[minz - 1, 0], colors=[colors[i], (0, 0, 0, 0)], alpha=alpha)

    handles = [Line2D([0], [0], color=colors[i], lw=2, label=eq) for i, eq in enumerate(eqs)]
    ax.legend(handles=handles, facecolor="#1e293b", labelcolor="white")
    ax.set_xlim(x_min, x_max)
    ax.set_ylim(y_min, y_max)

    canvas = FigureCanvasTkAgg(fig, master=win)
    canvas.draw()
    toolbar = NavigationToolbar2Tk(canvas, win)
    canvas.get_tk_widget().pack(fill="both", expand=True, padx=12, pady=12)
    toolbar.pack(fill="x", padx=10)