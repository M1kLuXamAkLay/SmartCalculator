from tkinter import filedialog
import traceback
import re
import configparser
import os
import subprocess
import time
import shutil


# ===================== ГЛОБАЛЬНЫЙ ЭКЗЕМПЛЯР PIX2TEXT (ленивая инициализация) =====================
_P2T = None


def _clean_math_text(text: str) -> str:
    """Улучшенная очистка: LaTeX → Python-выражение."""
    if not text:
        return ""
    
    text = re.sub(r'\^{([^}]*)}', r'**\1', text)
    text = re.sub(r'\\sqrt\{([^}]*)\}', r'sqrt(\1)', text)
    text = re.sub(r'\\sqrt\s*([^{}]+)', r'sqrt(\1)', text)
    text = re.sub(r'\\frac\s*\{([^}]*)\}\s*\{([^}]*)\}', r'(\1)/(\2)', text)
    
    for func in ['sin', 'cos', 'tan', 'ctg', 'cot', 'ln', 'log', 'lg', 'abs', 'pi']:
        text = re.sub(r'\\' + func, func, text)
    
    text = text.replace('{', '').replace('}', '')
    for cmd in ['mathbf', 'boldsymbol', 'bold', 'mathrm', 'text', 'bf', 'it', 'left', 'right']:
        text = text.replace('\\' + cmd, '')
    text = re.sub(r'\\([a-zA-Z!]+)', '', text)
    
    text = re.sub(r'^\s*[\$\\\[]+|\s*[\$\\\]]+\s*$', '', text)
    text = re.sub(r'\s*([=<>+\-*/])\s*', r'\1', text)
    text = re.sub(r'\s*\(\s*', '(', text)
    text = re.sub(r'\s*\)\s*', ')', text)
    
    text = text.replace('−', '-').replace('×', '*').replace('÷', '/')
    text = re.sub(r'(\d)\s+([a-zA-Z(])', r'\1*\2', text)
    text = re.sub(r'([a-zA-Z)])\s+(\d)', r'\1*\2', text)
    
    text = re.sub(r'[ \t]+', ' ', text).strip()
    return text


def _format_ollama_pull(line: str, model_name: str) -> str | None:
    """ИСПРАВЛЕННАЯ ВЕРСИЯ + ПОКАЗ ОШИБОК OLLAMA"""
    original_line = line.strip()
    if not original_line:
        return None

    if re.search(r'(?i)\b(error|failed|не удалось|ошибка|abort|not found|cannot|permission|disk|network|pulling manifest failed)', original_line):
        return f"❌ ОШИБКА OLLAMA: {original_line}"

    clean_line = re.sub(r'в-U|K0|\?[\d]+h?|1G|AI|pulling manifest', '', original_line, flags=re.IGNORECASE).strip()
    clean_line = re.sub(r'(?i)pulling\s+[^:]+:', f'Скачиваю {model_name}:', clean_line)

    percent_match = re.search(r'(\d+)%', clean_line)
    if percent_match:
        percent = int(percent_match.group(1))
        bar_length = 30
        filled = int(percent * bar_length / 100)
        bar = "█" * filled + "░" * (bar_length - filled)
        main_line = f'Скачиваю {model_name}: {percent}% {bar}'

        speed_match = re.search(r'(\d+(?:\.\d+)?)\s*(MB|GB)\s*/\s*(\d+(?:\.\d+)?)\s*(MB|GB)\s*(\d+(?:\.\d+)?\s*MB/s)?', original_line, re.IGNORECASE)
        if speed_match:
            left = speed_match.group(1)
            left_unit = speed_match.group(2)
            right = speed_match.group(3)
            right_unit = speed_match.group(4)
            speed = speed_match.group(5) or ''
            speed_str = f"{left} {left_unit}/{right} {right_unit}"
            if speed:
                speed_str += f" {speed}"
            return main_line + "\n" + speed_str
        return main_line

    if 'manifest' in original_line.lower():
        return f'Скачиваю {model_name}: подготовка...'

    if 'Скачиваю' in clean_line:
        return clean_line
    return None


def _clean_ai_response(text: str) -> str:
    """НОВОЕ: Очищает Markdown + LaTeX от нейросети в удобный читаемый текст для .txt и окна"""
    if not text:
        return ""

    # 1. Убираем все Markdown-заголовки (##, ###, #### и т.д.)
    text = re.sub(r'^#{1,6}\s*', '', text, flags=re.MULTILINE)

    # 2. Убираем жирный/курсив **текст** → текст
    text = re.sub(r'\*\*?(.*?)\*\*?', r'\1', text)

    # 3. Убираем пустые строки (больше 2 подряд → 2)
    text = re.sub(r'\n{3,}', '\n\n', text)

    # 4. Лёгкая чистка LaTeX (оставляем формулы, но делаем их читаемыми в .txt)
    text = text.replace('\\(', '(').replace('\\)', ')')
    text = text.replace('\\[', '').replace('\\]', '')
    text = re.sub(r'\\quad', '    ', text)          # отступы
    text = re.sub(r'\\geq', '≥', text)
    text = re.sub(r'\\leq', '≤', text)
    text = re.sub(r'\\implies', '⇒', text)
    text = re.sub(r'\\in', '∈', text)
    text = re.sub(r'\\inf', '∞', text)
    text = re.sub(r'\\sqrt', '√', text)
    text = re.sub(r'\\frac\{([^}]*)\}\{([^}]*)\}', r'(\1)/(\2)', text)

    # 5. Финальная нормализация
    text = text.strip()
    text = re.sub(r'[ \t]+', ' ', text)             # лишние пробелы
    text = re.sub(r'\n\s*\n', '\n\n', text)         # чистые абзацы

    return text


def get_ai_config():
    config = configparser.ConfigParser()
    config_path = "config.txt"
    if os.path.exists(config_path):
        config.read(config_path)
    if not config.has_section('AI'):
        config['AI'] = {'model': 'deepseek-r1:8b', 'temperature': '0.3'}
        with open(config_path, 'w', encoding='utf-8') as f:
            config.write(f)
    ai = config['AI']
    model = ai.get('model', 'deepseek-r1:8b')
    try:
        temperature = float(ai.get('temperature', '0.3'))
    except:
        temperature = 0.3
    return model, temperature


def ensure_ollama_running_and_model(progress_callback=None, stop_event=None) -> str | None:
    """Автоустановка Ollama + скачивание (ошибки видны)."""
    def status(msg: str):
        if progress_callback is not None:
            progress_callback(msg)
        else:
            print(f"[INFO] {msg}")

    status("Проверка наличия Ollama...")

    if shutil.which("ollama") is None:
        status("❌ Ollama не установлен.")
        status("⚠️ ВНИМАНИЕ: НЕ ЗАКРЫВАЙТЕ ПРОГРАММУ во время установки Ollama и скачивания модели! Это может занять 2–10 минут.")
        if stop_event is not None and stop_event.is_set():
            return "❌ Установка Ollama остановлена пользователем."
        status("🚀 Запускаю автоматическую установку с официального сайта...")
        status("⏳ Это может занять 2–10 минут. Не закрывайте программу!")
        try:
            proc = subprocess.Popen(
                ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command",
                 "irm https://ollama.com/install.ps1 | iex"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            for line in iter(proc.stdout.readline, ""):
                if line.strip():
                    status(f"Установка: {line.strip()}")
            proc.wait(timeout=900)
            if proc.returncode == 0:
                status("✅ Ollama успешно установлен!")
                status("⚠️ Перезапустите калькулятор для применения изменений.")
                return "✅ Ollama установлен автоматически.\nПерезапустите программу и повторите действие."
            else:
                return f"❌ Установка Ollama завершилась с ошибкой (код {proc.returncode})."
        except subprocess.TimeoutExpired:
            return "❌ Таймаут установки Ollama (15 мин)."
        except Exception as e:
            return f"❌ Ошибка при установке Ollama: {e}"

    import ollama
    status("✅ Ollama найден. Проверяю сервер...")

    server_running = False
    try:
        ollama.list()
        server_running = True
    except Exception as e:
        error_str = str(e).lower()
        server_running = not ("connection refused" in error_str or "failed to connect" in error_str)

    if not server_running:
        status("Сервер Ollama не запущен → запускаю автоматически...")
        try:
            subprocess.Popen(
                ['ollama', 'serve'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            time.sleep(5)
            status("✅ Сервер Ollama запущен.")
        except Exception as e:
            return f"❌ Не удалось запустить Ollama: {e}"

    model, _ = get_ai_config()
    status(f"Проверка модели {model}...")

    has_model = False
    try:
        response = ollama.list()
        if isinstance(response, dict) and 'models' in response:
            models_list = response['models']
            model_names = [m.get('name', m.get('model', str(m))) if isinstance(m, dict) else str(m) for m in models_list]
        elif hasattr(response, 'models'):
            models_list = response.models
            model_names = [getattr(m, 'name', getattr(m, 'model', str(m))) for m in models_list]
        else:
            model_names = []
        base_model = model.split(':')[0] if ':' in model else model
        has_model = any(base_model in name for name in model_names)
    except Exception:
        has_model = False

    if not has_model:
        status(f"📥 Модель {model} не найдена → начинаю скачивание...")
        try:
            proc = subprocess.Popen(
                ['ollama', 'pull', model],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            for line in iter(proc.stdout.readline, ""):
                if stop_event is not None and stop_event.is_set():
                    proc.terminate()
                    proc.wait()
                    return "❌ Скачивание модели остановлено пользователем."
                cleaned = line.strip()
                if cleaned:
                    formatted = _format_ollama_pull(cleaned, model)
                    if formatted is not None:
                        status(f"📥 {formatted}")
            proc.wait()
            if stop_event is not None and stop_event.is_set():
                return "❌ Скачивание модели остановлено пользователем."
            if proc.returncode == 0:
                status(f"✅ Модель {model} успешно скачана!")
            else:
                return f"❌ Скачивание завершилось с ошибкой (код {proc.returncode})."
        except Exception as e:
            return f"❌ Ошибка скачивания модели: {e}"
    else:
        status(f"✅ Модель {model} уже установлена.")

    return None


def recognize_from_photo(file_path: str | None = None) -> str:
    """Распознаёт текст/формулы с фото."""
    if file_path is None:
        file = filedialog.askopenfilename(filetypes=[("Images", "*.png *.jpg *.jpeg *.webp")])
        if not file:
            return ""
        file_path = file

    global _P2T
    if _P2T is None:
        try:
            import pix2text
            _P2T = pix2text.Pix2Text.from_config()
            print("[INFO] Pix2Text успешно инициализирован")
        except Exception as e:
            _P2T = None
            print(f"[ОШИБКА] Pix2Text: {e}")
            return "Ошибка: Pix2Text не установлен"

    if _P2T is None:
        return "Ошибка: Pix2Text не установлен"

    try:
        result = _P2T.recognize(file_path, resized_shape=768, return_text=True)
        raw_latex = str(result).strip()
        latex = _clean_math_text(raw_latex)
        print(f"[DEBUG] ОЧИЩЕНО: {latex}")
        return latex if latex.strip() else ""
    except Exception as e:
        print(f"[WARNING] Pix2Text ошибка: {e}")
        try:
            result = _P2T.recognize(file_path, resized_shape=768)
            raw_latex = str(result).strip()
            return _clean_math_text(raw_latex)
        except:
            traceback.print_exc()
            return ""


def solve_with_ai(task_text: str, progress_callback=None, stop_event=None) -> str:
    """Решение через ИИ + ОЧИСТКА Markdown → удобный текст"""
    import ollama
    model, temperature = get_ai_config()
    
    error = ensure_ollama_running_and_model(progress_callback=progress_callback, stop_event=stop_event)
    if error:
        return error

    prompt = f"""Задача ЕГЭ профильная математика:\n{task_text}\n\nРеши подробно по шагам (ФИПИ):\n1. Что дано\n2. Чертеж (описание) если задача на геометрию\n3. Решение\n4. Ответ"""
    try:
        stream_response = ollama.chat(
            model=model,
            messages=[{'role': 'user', 'content': prompt}],
            options={'temperature': temperature},
            stream=True
        )
        full_content = ""
        for chunk in stream_response:
            if stop_event is not None and stop_event.is_set():
                return "❌ Решение остановлено пользователем."
            content = chunk.get('message', {}).get('content', '')
            if content:
                full_content += content
        # ← НОВАЯ ОЧИСТКА: Markdown → чистый читаемый текст
        return _clean_ai_response(full_content)
    except Exception as e:
        print(f"[ОШИБКА ИИ] {e}")
        traceback.print_exc()
        return f"Ошибка ИИ: {e}"