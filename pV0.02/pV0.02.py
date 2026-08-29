import subprocess
import tempfile
import os
import requests
import sys
import json

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "richardyoung/qwen3-4b-instruct-2507-abliterated:latest"
TIMEOUT = 120  # увеличенный таймаут для загрузки модели

def ask(prompt):
    full_prompt = f"<|im_start|>system\nТы — ассистент, который пишет только код Python без пояснений.<|im_end|>\n<|im_start|>user\n{prompt}<|im_end|>\n<|im_start|>assistant\n"
    payload = {
        "model": MODEL,
        "prompt": full_prompt,
        "stream": False,
        "options": {"temperature": 0.3}
    }
    try:
        print("[Zed] Отправка запроса к Ollama...")
        r = requests.post(OLLAMA_URL, json=payload, timeout=TIMEOUT)
        r.raise_for_status()
        data = r.json()
        if "response" in data:
            return data["response"]
        else:
            raise Exception(f"Неизвестный формат ответа: {data}")
    except requests.exceptions.Timeout:
        print(f"[Zed] ❌ Таймаут: Ollama не ответил за {TIMEOUT} секунд.")
        print("Проверь, что Ollama запущен и модель загружена (можно выполнить 'ollama list').")
        sys.exit(1)
    except Exception as e:
        print(f"[Zed] ❌ Ошибка при запросе к Ollama: {e}")
        sys.exit(1)

def extract_code(text):
    if "```python" in text:
        parts = text.split("```python")
        if len(parts) > 1:
            code = parts[1].split("```")[0].strip()
            return code
    # Если нет маркеров, но это похоже на код — оставляем как есть
    return text.strip()

def run_python(code):
    with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as f:
        f.write(code.encode())
        path = f.name
    try:
        res = subprocess.run(
            [sys.executable, path],
            capture_output=True,
            text=True,
            timeout=5
        )
        os.unlink(path)
        if res.returncode == 0:
            return {"ok": True, "out": res.stdout.strip()}
        else:
            err = res.stderr.strip() or res.stdout.strip()
            return {"ok": False, "err": err}
    except subprocess.TimeoutExpired:
        os.unlink(path)
        return {"ok": False, "err": "TimeoutError: код выполнялся слишком долго"}
    except Exception as e:
        os.unlink(path)
        return {"ok": False, "err": str(e)}

TASK = """
Напиши функцию factorial(n), которая возвращает факториал числа n.
Если n < 0, возвращает None.
Не используй math.factorial. Реализуй через рекурсию или цикл.

После определения функции добавь следующий код для проверки:
if __name__ == "__main__":
    tests = [
        (5, 120),
        (0, 1),
        (1, 1),
        (-1, None),
        (3, 6)
    ]
    for n, expected in tests:
        result = factorial(n)
        if result != expected:
            print(f"FAIL: factorial({n}) returned {result}, expected {expected}")
            exit(1)
    print("ALL TESTS PASSED")
"""

print("[Zed] Задача:")
print(TASK)

history = []
code = ""

for i in range(5):
    print(f"\n--- Итерация {i+1} ---")
    if i == 0:
        prompt = f"{TASK}\nНапиши только код Python (включая тесты в __main__):"
    else:
        errors = "\n".join(history[-3:])
        prompt = f"Твой код выдал ошибку или провалил тесты:\n{errors}\nИсправь код. Напиши только исправленный код (включая тесты):"
    
    raw = ask(prompt)
    code = extract_code(raw)
    print("[Zed] Код:")
    print(code)
    
    result = run_python(code)
    if result["ok"]:
        if "ALL TESTS PASSED" in result["out"]:
            print(f"[Zed] ✅ Все тесты пройдены! Вывод: {result['out']}")
            break
        else:
            err_msg = result["out"]
            print(f"[Zed] ❌ Тесты провалены: {err_msg}")
            history.append(f"Тесты провалены: {err_msg}")
    else:
        err = result["err"]
        print(f"[Zed] ❌ Ошибка выполнения:\n{err}")
        history.append(f"Ошибка выполнения:\n{err}\nКод:\n{code}")
else:
    print("[Zed] ❌ Не удалось исправить за 5 попыток.")