"""Завантаження вихідних файлів наборів даних SaveEcoBot з порталу data.gov.ua.

Запуск з кореня репозиторію:
    python scripts/download_data.py                      # міста, 2021–2023
    python scripts/download_data.py --years 2022 2023    # лише вибрані роки
    python scripts/download_data.py --districts          # додатково дані за районами міст

Файли зберігаються в data/raw/. Якщо файл уже є, повторно він не завантажується.

Набори (розпорядник — ГО «SaveDnipro», ліцензія CC BY):
* «Щогодинні концентрації та індекс якості атмосферного повітря для дрібнодисперсного пилу
  фракції 2.5 мікронів в населених пунктах України»
* те саме «...в районах населених пунктів України»
"""
import argparse
from pathlib import Path
import shutil
from urllib.request import Request, urlopen

CITIES = "https://data.gov.ua/dataset/402d427f-f024-465a-97a9-5ed29f510015/resource"
DISTRICTS = "https://data.gov.ua/dataset/12362dc6-6252-439d-b36e-26d0d085733f/resource"

CITY_FILES = {
    "dict": (f"{CITIES}/be416b15-efa2-44d8-a7cd-5a3641ca4ecf", "saveecobot_aqi_cities.csv"),
    2019: (f"{CITIES}/02a18eae-25d2-4b58-9c87-1d474685b31a", "saveecobot_cities_pm25_and_aqi_pm25_2019.csv"),
    2020: (f"{CITIES}/ee50c8d8-1f37-4583-843e-3e1abc4f9bcc", "saveecobot_cities_pm25_and_aqi_pm25_2020.csv"),
    2021: (f"{CITIES}/0ef1cf7d-b43d-44a9-8086-9176462e04fe", "saveecobot_cities_pm25_and_aqi_pm25_2021.csv"),
    2022: (f"{CITIES}/887c55ba-8eaf-4746-a801-d7303296742c", "saveecobot_cities_pm25_and_aqi_pm25_2022.csv"),
    2023: (f"{CITIES}/20741668-79e2-48a0-9954-cdf55a845738", "saveecobot_cities_pm25_and_aqi_pm25_2023.csv"),
}
DISTRICT_FILES = {
    "dict": (f"{DISTRICTS}/bf40b7f0-e296-441c-afdb-43c3ac633cff", "saveecobot_city_districts.csv"),
    2019: (f"{DISTRICTS}/919a8fd9-1bbd-4945-995e-806ccd90613a", "saveecobot_city_districts_pm25_and_aqi_pm25_2019.csv"),
    2020: (f"{DISTRICTS}/ad9a947b-f94f-49c7-9fbf-16ca08ee8898", "saveecobot_city_districts_pm25_and_aqi_pm25_2020.csv"),
    2021: (f"{DISTRICTS}/97c7989b-34b1-4b08-9fec-1813a4298140", "saveecobot_city_districts_pm25_and_aqi_pm25_2021.csv"),
    2022: (f"{DISTRICTS}/dc1620ca-9b56-445a-aafa-e6081f52064d", "saveecobot_city_districts_pm25_and_aqi_pm25_2022.csv"),
    2023: (f"{DISTRICTS}/cd108421-7797-47fb-ab6e-99f1abc7f56b", "saveecobot_city_districts_pm25_and_aqi_pm25_2023.csv"),
}

RAW = Path(__file__).resolve().parent.parent / "data" / "raw"


def fetch(base_and_name):
    base, name = base_and_name
    target = RAW / name
    if target.exists():
        print(f"вже є: {name}")
        return
    print(f"завантажую {name} ...", flush=True)
    req = Request(f"{base}/download/{name}", headers={"User-Agent": "Mozilla/5.0 (PR4 student script)"})
    part = target.with_suffix(".part")          # спершу пишемо в тимчасовий файл,
    with urlopen(req, timeout=120) as resp, open(part, "wb") as out:
        shutil.copyfileobj(resp, out)
    part.rename(target)                          # щоб обірване завантаження не лишило «битий» CSV
    print(f"  готово, {target.stat().st_size / 1e6:.1f} МБ")


def main():
    parser = argparse.ArgumentParser(description="Завантаження даних SaveEcoBot з data.gov.ua")
    parser.add_argument("--years", nargs="+", type=int, default=[2021, 2022, 2023])
    parser.add_argument("--districts", action="store_true", help="також дані за районами міст")
    args = parser.parse_args()
    RAW.mkdir(parents=True, exist_ok=True)

    fetch(CITY_FILES["dict"])
    for y in args.years:
        fetch(CITY_FILES[y])
    if args.districts:
        fetch(DISTRICT_FILES["dict"])
        for y in args.years:
            fetch(DISTRICT_FILES[y])


if __name__ == "__main__":
    main()
