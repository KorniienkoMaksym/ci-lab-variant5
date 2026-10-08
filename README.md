# ![CI](https://github.com/KorniienkoMaksym/ci-lab-variant5/actions/workflows/ci.yml/badge.svg) ![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)

# Практична робота: CI-конвеєр на GitHub Actions

Навчальна лабораторна робота (Варіант 5). 

**Проєкт містить:**
* `number_theory.py` — математичні функції (перевірка простого числа, факторіал, парність).
* `test_number_theory.py` — автоматичні тести.
* CI-конвеєр, який автоматично перевіряє код за допомогою `pytest` при кожному оновленні.

## Запуск через Docker

```bash
docker pull ghcr.io/<ваш-логін>/ci-lab-app:latest
docker run --rm ghcr.io/<ваш-логін>/ci-lab-app:latest
```
## CI/CD-конвеєр 
Source -> Build -> Test -> Package -> Deploy 
При кожному push у гілку main автоматично: встановлюються залежності, 
запускаються тести, збирається й публікується Docker-образ у GHCR, 
після чого Terraform розгортає цей образ і перевіряє результат. 
