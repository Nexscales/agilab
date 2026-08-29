import subprocess
import tempfile
import os
import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "richardyoung/qwen3-4b-instruct-2507-abliterated:latest"  # или твоя модель

def ask(prompt):
    r = requests.post(OLLAMA_URL, json={"model": MODEL, "prompt": prompt, "stream": False})
    return r.json()["response"]

def extract_code(text):
    if "```python" in text:
        return text.split("```python")[1].split("```")[0].strip()
    return text.strip()

def run_python(code):
    with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as f:
        f.write(code.encode())
        path = f.name
    try:
        res = subprocess.run(["python3", path], capture_output=True, text=True, timeout=5)
        os.unlink(path)
        if res.returncode == 0:
            return {"ok": True, "out": res.stdout.strip()}
        return {"ok": False, "err": res.stderr.strip()}
    except Exception as e:
        os.unlink(path)
        return {"ok": False, "err": str(e)}

# ---- ЗАДАЧА: написать функцию factorial(n) с защитой от отрицательных чисел ----
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
            # тесты не пройдены, но код выполнился без ошибок (например, напечатал FAIL)
            err_msg = result["out"]
            print(f"[Zed] ❌ Тесты провалены: {err_msg}")
            history.append(f"Тесты провалены: {err_msg}")
    else:
        err = result["err"]
        print(f"[Zed] ❌ Ошибка выполнения:\n{err}")
        history.append(f"Ошибка выполнения:\n{err}\nКод:\n{code}")
else:
    print("[Zed] ❌ Не удалось исправить за 5 попыток.")