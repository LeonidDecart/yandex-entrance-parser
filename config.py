# Ротация прокси при запуске браузера. PROXIES не должен быть пустым (минимум один элемент).
# 
# Случай 1: Без прокси
# PROXIES = [None]
# 
# Случай 2: Только прокси
# PROXIES = [
#     {"host": "proxy1.example.com", "port": 8080, "user": "username1", "pass": "password1"},
#     {"host": "proxy2.example.com", "port": 8080, "user": "username2", "pass": "password2"},
# ]
# 
# Случай 3: Гибрид (None + прокси)
# PROXIES = [
#     None,
#     {"host": "proxy1.example.com", "port": 8080, "user": "username1", "pass": "password1"},
# ]
# Ротация по кругу: None → proxy1 → None → proxy1...
# 
# Формат: host (IP/домен), port (8080/3128/1080), user, pass
PROXIES = [
    None,
]

