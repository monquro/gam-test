# -*- coding: utf-8 -*-
"""포토부스 대목 달력 — 공개 데이터 받기 + 지역별 정답 계산.

지역(매장이 있는 도시) × 테마 6개 × 3문항. **모든 숫자는 원본에서 계산합니다.**

  날씨   Open-Meteo Archive (ERA5 고정) — 2016~2025 일별 강수·기온·구름·일몰
  공휴일 Nager.Date — 나라별 공휴일. 연휴(3일 이상 연속으로 쉬는 날)는 여기서 직접 센다

원본은 data/raw/photobox/ 에 저장되고 (git·배포 제외), 결과는 photoday/photobox.json 하나로 나갑니다.

실행 (저장소 최상위에서):
    python tools/build_photobox.py
    python tools/build_photobox.py --force     # 원본을 다시 받는다
"""
from __future__ import annotations

import datetime as dt
import json
import sys
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

HERE = Path(__file__).resolve().parent
APP = HERE.parent
RAW = APP / "data" / "raw" / "photobox"
OUT = APP / "photoday" / "photobox.json"   # PHOTO DAY 화면이 있는 폴더
UA = {"User-Agent": "gam-test-class/1.0 (data analysis class)"}
FORCE = "--force" in sys.argv

Y0, Y1 = 2016, 2025            # 날씨는 최근 10년
YEARS = Y1 - Y0 + 1
NEXT = 2027                    # 연휴 문항은 다가오는 해
RAIN_MM = 1.0                  # 비 온 날 = 하루 강수량 1mm 이상
CLEAR_CLOUD = 40               # 맑은 날 = 비 1mm 미만 + 하루 평균 구름양 40% 이하

# 미국은 매장이 있는 지역만, 한국은 광역시와 제주. 같은 도시의 매장은 날씨가 같으므로 한 지역으로 묶는다.
REGIONS = [
    ("la", "US", 34.0617, -118.3005,
     ("LA 코리아타운", "Los Angeles (Koreatown)", "Los Ángeles (Koreatown)")),
    ("pleasanton", "US", 37.6946, -121.9289,
     ("플레전턴", "Pleasanton, CA", "Pleasanton, CA")),
    ("milpitas", "US", 37.4159, -121.8977,
     ("밀피타스", "Milpitas, CA", "Milpitas, CA")),
    ("honolulu", "US", 21.2911, -157.8437,
     ("호놀룰루", "Honolulu, HI", "Honolulu, HI")),
    ("carrollton", "US", 32.9988, -96.9098,
     ("캐럴턴", "Carrollton, TX", "Carrollton, TX")),
    ("frisco", "US", 33.0987, -96.8125,
     ("프리스코", "Frisco, TX", "Frisco, TX")),
    ("annarbor", "US", 42.2797, -83.7445,
     ("앤아버", "Ann Arbor, MI", "Ann Arbor, MI")),
    ("seoul", "KR", 37.5665, 126.9780, ("서울", "Seoul", "Seúl")),
    ("busan", "KR", 35.1796, 129.0756, ("부산", "Busan", "Busan")),
    ("incheon", "KR", 37.4563, 126.7052, ("인천", "Incheon", "Incheon")),
    ("daegu", "KR", 35.8714, 128.6014, ("대구", "Daegu", "Daegu")),
    ("daejeon", "KR", 36.3504, 127.3845, ("대전", "Daejeon", "Daejeon")),
    ("gwangju", "KR", 35.1595, 126.8526, ("광주", "Gwangju", "Gwangju")),
    ("ulsan", "KR", 35.5384, 129.3114, ("울산", "Ulsan", "Ulsan")),
    ("jeju", "KR", 33.4996, 126.5312, ("제주", "Jeju", "Jeju")),
]
COUNTRY = {"US": ("미국", "United States", "Estados Unidos"),
           "KR": ("한국", "South Korea", "Corea del Sur")}


def T(ko, en, es):
    return {"ko": ko, "en": en, "es": es}


# ════════════════════════════════════════════════════════════════
# 받기
# ════════════════════════════════════════════════════════════════
def get(name, url):
    path = RAW / name
    if path.exists() and not FORCE:
        return json.loads(path.read_text(encoding="utf-8"))
    RAW.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers=UA)
    # Open-Meteo 는 1분에 받을 수 있는 양이 정해져 있다(429). 서버가 잠깐 멈출 때도 있다(5xx)
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                body = r.read().decode("utf-8")
            break
        except urllib.error.HTTPError as e:
            if (e.code != 429 and e.code < 500) or attempt == 3:
                raise
            wait = 65 if e.code == 429 else 5
            print(f"  {name}: HTTP {e.code} — {wait}초 쉬고 다시 받습니다")
            time.sleep(wait)
    path.write_text(body, encoding="utf-8")
    print(f"  받음 {name} ({len(body) // 1024}KB)")
    time.sleep(0.4)
    return json.loads(body)


# 받을 주소 — tools/fetch_all.py 도 같은 주소로 받는다
def weather_url(lat, lon):
    return ("https://archive-api.open-meteo.com/v1/archive"
            f"?latitude={lat}&longitude={lon}"
            f"&start_date={Y0}-01-01&end_date={Y1}-12-31"
            "&daily=precipitation_sum,temperature_2m_max,temperature_2m_min,"
            "cloud_cover_mean,sunset,daylight_duration"
            "&timezone=auto&models=era5")


def holiday_url(country, year):
    return f"https://date.nager.at/api/v3/PublicHolidays/{year}/{country}"


# 지난 10년의 연휴 + 다가오는 해(NEXT)와 해를 넘기는 연휴를 보려고 그다음 해까지
HOLIDAY_YEARS = range(Y0, NEXT + 2)


def weather(rid, lat, lon):
    d = get(f"weather_{rid}.json", weather_url(lat, lon))["daily"]
    rows = []
    for i, t in enumerate(d["time"]):
        rows.append({"d": dt.date.fromisoformat(t),
                     "rain": d["precipitation_sum"][i] or 0.0,
                     "hi": d["temperature_2m_max"][i],
                     "lo": d["temperature_2m_min"][i],
                     "cloud": d["cloud_cover_mean"][i],
                     "sunset": d["sunset"][i][11:16],
                     "daylight": d["daylight_duration"][i] / 3600})
    return rows


# Nager.Date 의 한국 과거 공휴일은 틀린 해가 있다 — 2008년에 빠진 제헌절이 들어 있고,
# 대체공휴일 자리에 원래 날짜가 밀려 있고, 선거일·임시공휴일이 없다.
# 그래서 2016~2025년은 관공서 공휴일 규정과 발표된 임시공휴일로 직접 적은 목록을 쓴다.
#   (대) 대체공휴일   (선) 선거일   (임) 임시공휴일
KR_HOLIDAYS = {
    2016: "01-01 02-07 02-08 02-09 02-10(대) 03-01 05-05 05-06(임) 05-14 06-06 08-15 "
          "09-14 09-15 09-16 10-03 10-09 12-25",
    2017: "01-01 01-27 01-28 01-29 01-30(대) 03-01 05-03 05-05 05-09(선) 06-06 08-15 "
          "10-02(임) 10-03 10-04 10-05 10-06(대) 10-09 12-25",
    2018: "01-01 02-15 02-16 02-17 03-01 05-05 05-07(대) 05-22 06-06 06-13(선) 08-15 "
          "09-23 09-24 09-25 09-26(대) 10-03 10-09 12-25",
    2019: "01-01 02-04 02-05 02-06 03-01 05-05 05-06(대) 05-12 06-06 08-15 "
          "09-12 09-13 09-14 10-03 10-09 12-25",
    2020: "01-01 01-24 01-25 01-26 01-27(대) 03-01 04-15(선) 04-30 05-05 06-06 08-15 08-17(임) "
          "09-30 10-01 10-02 10-03 10-09 12-25",
    2021: "01-01 02-11 02-12 02-13 03-01 05-05 05-19 06-06 08-15 08-16(대) "
          "09-20 09-21 09-22 10-03 10-04(대) 10-09 10-11(대) 12-25",
    2022: "01-01 01-31 02-01 02-02 03-01 03-09(선) 05-05 05-08 06-01(선) 06-06 08-15 "
          "09-09 09-10 09-11 09-12(대) 10-03 10-09 10-10(대) 12-25",
    2023: "01-01 01-21 01-22 01-23 01-24(대) 03-01 05-05 05-27 05-29(대) 06-06 08-15 "
          "09-28 09-29 09-30 10-02(임) 10-03 10-09 12-25",
    2024: "01-01 02-09 02-10 02-11 02-12(대) 03-01 04-10(선) 05-05 05-06(대) 05-15 06-06 08-15 "
          "09-16 09-17 09-18 10-01(임) 10-03 10-09 12-25",
    2025: "01-01 01-27(임) 01-28 01-29 01-30 03-01 03-03(대) 05-05 05-06(대) 06-03(선) 06-06 08-15 "
          "10-03 10-05 10-06 10-07 10-08(대) 10-09 12-25",
}
# 2026년부터는 Nager.Date 가 맞다(제헌절·노동절 공휴일 포함). 2027년 성탄절(토) 대체공휴일만 빠져 있다
KR_ADD = {2027: ["12-27"]}


def days_off(country, year):
    """그 해에 쉬는 날(토·일 + 전국 공휴일)과 공휴일 수."""
    hol = get(f"holidays_{country}_{year}.json", holiday_url(country, year))
    # 미국은 연방 공휴일만 (주마다 다른 날은 뺀다)
    hols = {dt.date.fromisoformat(h["date"]) for h in hol
            if h["global"] and "Public" in h["types"]}
    if country == "KR" and year in KR_HOLIDAYS:
        hols = {dt.date.fromisoformat(f"{year}-{x[:5]}") for x in KR_HOLIDAYS[year].split()}
    if country == "KR":
        hols |= {dt.date.fromisoformat(f"{year}-{x}") for x in KR_ADD.get(year, [])}
    days = set(hols)
    d = dt.date(year, 1, 1)
    while d.year == year:
        if d.weekday() >= 5:
            days.add(d)
        d += dt.timedelta(days=1)
    return days, len(hols)


def long_weekends(country, year):
    """3일 이상 이어서 쉬는 묶음. 휴가를 따로 내야 이어지는 날(징검다리)은 넣지 않는다."""
    off = set()
    for y in (year - 1, year, year + 1):       # 해를 넘기는 연휴를 자르지 않는다
        if y >= Y0:
            off |= days_off(country, y)[0]
    runs, cur = [], []
    for d in sorted(off):
        if cur and d - cur[-1] == dt.timedelta(days=1):
            cur.append(d)
        else:
            if len(cur) >= 3:
                runs.append(cur)
            cur = [d]
    if len(cur) >= 3:
        runs.append(cur)
    return [r for r in runs if r[0].year == year]


# ════════════════════════════════════════════════════════════════
# 문항 도구
# ════════════════════════════════════════════════════════════════
def q_num(qid, text, answer, unit, step, basis, why, lo=0, hi=None):
    """보기 3개: 정답과 위·아래로 한 칸씩. 한 칸은 정답의 35% 쯤, 최소 step."""
    a = round(answer) if step >= 1 else round(answer, 1)
    k = max(step, round(abs(a) * 0.35 / step) * step)
    opts = [a - k, a, a + k]
    if opts[0] < lo:
        opts = [a, a + k, a + 2 * k]
    if hi is not None and opts[-1] > hi:
        opts = [a - 2 * k, a - k, a]
    opts = [round(o, 1) if step < 1 else int(o) for o in opts]
    return {"id": qid, "kind": "num", "text": text, "options": opts,
            "answer": opts[opts.index(a if step < 1 else int(a))],
            "unit": unit, "basis": basis, "why": why}


def q_month(qid, text, scores, basis, why, best=max):
    """scores = {월: 값}. 정답 + 1위보다 확실히 낮은 달 둘 (달 순서대로).

    공동 1위가 있으면 그중 이른 달 하나만 보기에 넣는다 — 보기 안에서 정답이 하나가 되게.
    """
    order = sorted(scores, key=lambda m: (-scores[m] if best is max else scores[m], m))
    ans = order[0]
    rest = [m for m in order if scores[m] != scores[ans]]
    if len(rest) < 2:
        return None
    opts = sorted({ans, rest[len(rest) // 2], rest[-1]})
    return {"id": qid, "kind": "month", "text": text, "options": opts,
            "answer": ans, "basis": basis, "why": why}


def q_pick(qid, kind, text, options, answer, basis, why):
    assert answer in options, qid
    return {"id": qid, "kind": kind, "text": text, "options": options,
            "answer": answer, "basis": basis, "why": why}


def hhmm(m):
    return f"{m // 60:02d}:{m % 60:02d}"


def mins(s):
    h, m = s.split(":")
    return int(h) * 60 + int(m)


def deg(c, unit):
    return c * 9 / 5 + 32 if unit == "F" else c


def ddeg(c, unit):               # 온도 '차이'는 32를 더하지 않는다
    return c * 9 / 5 if unit == "F" else c


SEASON = {12: "winter", 1: "winter", 2: "winter", 3: "spring", 4: "spring", 5: "spring",
          6: "summer", 7: "summer", 8: "summer", 9: "fall", 10: "fall", 11: "fall"}
DAYS = T("일", " days", " días")
TIMES = T("번", " times", " veces")
HOURS = T("시간", " hours", " horas")
MON_KO = "1월 2월 3월 4월 5월 6월 7월 8월 9월 10월 11월 12월".split()


# ════════════════════════════════════════════════════════════════
# 테마별 문항
# ════════════════════════════════════════════════════════════════
def rainy_theme(W, nm):
    wk = [x for x in W if x["d"].weekday() >= 5]
    wet = [x for x in wk if x["rain"] >= RAIN_MM]
    per_year = len(wet) / YEARS
    by_m = Counter(x["d"].month for x in wet)
    m_scores = {m: by_m.get(m, 0) / YEARS for m in range(1, 13)}
    seas = defaultdict(float)
    for x in W:
        seas[SEASON[x["d"].month]] += x["rain"] / YEARS
    s_ans = max(seas, key=seas.get)
    qs = [
        q_num("r1",
              T(f"{nm['ko']}에서 비 오는 주말(토·일)은 1년에 며칠쯤일까?",
                f"In {nm['en']}, how many weekend days (Sat/Sun) a year get rain?",
                f"En {nm['es']}, ¿cuántos días de fin de semana al año llueve?"),
              per_year, DAYS, 1,
              T(f"{Y0}~{Y1}년 토·일 중 하루 강수량 {RAIN_MM:g}mm 이상인 날을 세어 평균하면 1년에 {per_year:.1f}일",
                f"Sat/Sun with ≥{RAIN_MM:g} mm of rain, {Y0}–{Y1}: {per_year:.1f} days a year on average",
                f"Sáb/dom con ≥{RAIN_MM:g} mm de lluvia, {Y0}–{Y1}: {per_year:.1f} días al año en promedio"),
              T("주말 약속이 비에 막히는 날이 1년에 이만큼. 그날의 플랜 B는 실내 📸",
                "That's how many weekend plans the rain can crash. Plan B: indoors 📸",
                "Esos son los findes que la lluvia puede arruinar. Plan B: bajo techo 📸")),
        q_month("r2",
                T("비 오는 주말이 가장 많은 달은?",
                  "Which month has the most rainy weekend days?",
                  "¿Qué mes tiene más días de fin de semana lluviosos?"),
                m_scores,
                T(f"{Y0}~{Y1}년 달마다 비 온 토·일을 세어 해마다 평균: " +
                  " · ".join(f"{MON_KO[m-1]} {m_scores[m]:.1f}일" for m in range(1, 13)),
                  f"Rainy Sat/Sun per month, {Y0}–{Y1} average: " +
                  " · ".join(f"{dt.date(2000, m, 1):%b} {m_scores[m]:.1f}" for m in range(1, 13)),
                  f"Sáb/dom lluviosos por mes, promedio {Y0}–{Y1}: " +
                  " · ".join(f"{m}: {m_scores[m]:.1f}" for m in range(1, 13))),
                T("그 달엔 실내 데이트 코스를 미리 찜해 두세요",
                  "Save an indoor date idea for that month",
                  "Guarda un plan bajo techo para ese mes")),
        q_pick("r3", "season",
               T("비가 가장 많이 내리는 계절은?",
                 "Which season gets the most rain?",
                 "¿Qué estación tiene más lluvia?"),
               ["spring", "summer", "fall", "winter"], s_ans,
               T(f"{Y0}~{Y1}년 계절별 강수량 합계의 연평균: 봄 {seas['spring']:.0f} · 여름 {seas['summer']:.0f} · "
                 f"가을 {seas['fall']:.0f} · 겨울 {seas['winter']:.0f}mm (봄 3~5월 · 여름 6~8월 · 가을 9~11월 · 겨울 12~2월)",
                 f"Average seasonal rain, {Y0}–{Y1}: spring {seas['spring']:.0f} · summer {seas['summer']:.0f} · "
                 f"fall {seas['fall']:.0f} · winter {seas['winter']:.0f} mm (Mar–May / Jun–Aug / Sep–Nov / Dec–Feb)",
                 f"Lluvia media por estación, {Y0}–{Y1}: primavera {seas['spring']:.0f} · verano {seas['summer']:.0f} · "
                 f"otoño {seas['fall']:.0f} · invierno {seas['winter']:.0f} mm (mar–may / jun–ago / sep–nov / dic–feb)"),
               T("비가 몰리는 계절엔 우산 대신 사진 한 장 ☔",
                 "Rainy season? Trade the umbrella for a photo ☔",
                 "¿Temporada de lluvias? Cambia el paraguas por una foto ☔")),
    ]
    return qs, m_scores


def sunny_theme(W, nm, unit):
    wk = [x for x in W if x["d"].weekday() >= 5]
    clear = [x for x in wk if x["rain"] < RAIN_MM and x["cloud"] <= CLEAR_CLOUD]
    per_year = len(clear) / YEARS
    by_m = Counter(x["d"].month for x in clear)
    c_scores = {m: by_m.get(m, 0) / YEARS for m in range(1, 13)}
    hot = defaultdict(list)
    for x in wk:
        hot[x["d"].month].append(x["hi"])
    h_scores = {m: sum(v) / len(v) for m, v in hot.items()}
    u = "°F" if unit == "F" else "°C"
    qs = [
        q_month("s1",
                T("맑은 주말이 가장 많은 달은?",
                  "Which month has the most clear weekend days?",
                  "¿Qué mes tiene más fines de semana despejados?"),
                c_scores,
                T(f"맑은 날 = 강수 {RAIN_MM:g}mm 미만 + 하루 평균 구름양 {CLEAR_CLOUD}% 이하. {Y0}~{Y1}년 달마다 맑은 토·일 평균: " +
                  " · ".join(f"{MON_KO[m-1]} {c_scores[m]:.1f}일" for m in range(1, 13)),
                  f"Clear = <{RAIN_MM:g} mm rain and ≤{CLEAR_CLOUD}% average cloud cover. Clear Sat/Sun per month, {Y0}–{Y1}: " +
                  " · ".join(f"{dt.date(2000, m, 1):%b} {c_scores[m]:.1f}" for m in range(1, 13)),
                  f"Despejado = <{RAIN_MM:g} mm de lluvia y ≤{CLEAR_CLOUD}% de nubes. Sáb/dom despejados por mes, {Y0}–{Y1}: " +
                  " · ".join(f"{m}: {c_scores[m]:.1f}" for m in range(1, 13))),
                T("밖에서 한 장, 부스에서 한 장 — 그 달이 기회예요",
                  "One shot outside, one in the booth — that's the month",
                  "Una foto afuera y otra en la cabina: ese es el mes")),
        q_month("s2",
                T("주말 낮 기온이 가장 높은 달은?",
                  "Which month has the hottest weekend afternoons?",
                  "¿Qué mes tiene las tardes de fin de semana más calurosas?"),
                h_scores,
                T(f"{Y0}~{Y1}년 토·일 낮 최고기온 평균이 가장 높은 달 — " +
                  " · ".join(f"{MON_KO[m-1]} {deg(h_scores[m], unit):.0f}{u}" for m in range(1, 13)),
                  f"Average Sat/Sun high, {Y0}–{Y1}: " +
                  " · ".join(f"{dt.date(2000, m, 1):%b} {deg(h_scores[m], unit):.0f}{u}" for m in range(1, 13)),
                  f"Máxima media de sáb/dom, {Y0}–{Y1}: " +
                  " · ".join(f"{m}: {deg(h_scores[m], unit):.0f}{u}" for m in range(1, 13))),
                T("더운 날엔 시원한 실내에서 친구랑 한 컷 🧊",
                  "Too hot out? Cool off inside with a friend 🧊",
                  "¿Mucho calor? Refréscate adentro con un amigo 🧊")),
        q_num("s3",
              T(f"{nm['ko']}에서 1년 중 맑은 주말(토·일)은 평균 며칠일까?",
                f"How many clear weekend days does {nm['en']} get a year?",
                f"¿Cuántos días de fin de semana despejados tiene {nm['es']} al año?"),
              per_year, DAYS, 1,
              T(f"강수 {RAIN_MM:g}mm 미만 + 구름양 {CLEAR_CLOUD}% 이하인 토·일, {Y0}~{Y1}년 평균 1년에 {per_year:.1f}일 (주말은 1년에 약 104일)",
                f"Sat/Sun with <{RAIN_MM:g} mm rain and ≤{CLEAR_CLOUD}% clouds, {Y0}–{Y1}: {per_year:.1f} a year (out of ~104 weekend days)",
                f"Sáb/dom con <{RAIN_MM:g} mm y ≤{CLEAR_CLOUD}% de nubes, {Y0}–{Y1}: {per_year:.1f} al año (de ~104 días de fin de semana)"),
              T("맑은 주말은 하늘이 준 촬영 날. 그날은 꼭 남겨 두세요",
                "A clear weekend is a free photo day — capture it",
                "Un finde despejado es un día de fotos: guárdalo")),
    ]
    return qs, c_scores


def holiday_theme(country, W):
    nm = {k: v for k, v in zip(("ko", "en", "es"), COUNTRY[country])}
    nm["en"] = {"US": "the U.S."}.get(country, nm["en"])     # 문장 안에서는 관사가 붙는다
    nm["es"] = {"US": "EE. UU."}.get(country, nm["es"])
    runs = long_weekends(country, NEXT)
    n_hol = days_off(country, NEXT)[1]
    longest = max(len(r) for r in runs)
    by_m = Counter()
    for r in runs:
        for d in r:
            by_m[d.month] += 1
    m_scores = {m: by_m.get(m, 0) for m in range(1, 13)}
    qs = [
        q_num("h1",
              T(f"{NEXT}년 {nm['ko']}에서 3일 이상 이어지는 연휴는 몇 번일까?",
                f"How many 3-day-plus weekends does {nm['en']} get in {NEXT}?",
                f"¿Cuántos puentes de 3 días o más tiene {nm['es']} en {NEXT}?"),
              len(runs), TIMES, 1,
              T(f"전국 공휴일과 토·일이 3일 이상 이어지는 묶음 (휴가를 내야 이어지는 징검다리는 제외): " +
                ", ".join(f"{r[0]:%m/%d}~{r[-1]:%m/%d}" for r in runs),
                f"National holidays + weekends, 3+ days in a row (no extra days off): " +
                ", ".join(f"{r[0]:%b %d}–{r[-1]:%b %d}" for r in runs),
                f"Feriados nacionales + fin de semana, 3+ días seguidos (sin días puente): " +
                ", ".join(f"{r[0]:%d/%m}–{r[-1]:%d/%m}" for r in runs)),
              T("단톡방에 날짜 공유할 차례 🎉",
                "Time to drop the dates in the group chat 🎉",
                "Hora de mandar las fechas al grupo 🎉")),
    ]
    q2 = q_month("h2",
                 T(f"{NEXT}년, 연휴로 쉬는 날이 가장 많은 달은?",
                   f"In {NEXT}, which month has the most long-weekend days?",
                   f"En {NEXT}, ¿qué mes tiene más días de puente?"),
                 m_scores,
                 T("달마다 3일 이상 연휴에 들어간 날 수: " +
                   " · ".join(f"{MON_KO[m-1]} {m_scores[m]}" for m in range(1, 13) if m_scores[m]),
                   "Long-weekend days per month: " +
                   " · ".join(f"{dt.date(2000, m, 1):%b} {m_scores[m]}" for m in range(1, 13) if m_scores[m]),
                   "Días de puente por mes: " +
                   " · ".join(f"{m}: {m_scores[m]}" for m in range(1, 13) if m_scores[m])),
                 T("그 달은 친구·가족 단위 방문이 몰리는 대목 후보",
                   "That month is prime time for friends and family visits",
                   "Ese mes es temporada alta para visitas con amigos y familia"))
    q_long = q_num("h2" if q2 is None else "h3",
                   T(f"{NEXT}년 가장 긴 연휴는 며칠일까?",
                     f"How long is the longest break in {NEXT}?",
                     f"¿Cuántos días dura el puente más largo de {NEXT}?"),
                   longest, DAYS, 1,
                   T(f"가장 긴 묶음: " + ", ".join(f"{r[0]:%m/%d}~{r[-1]:%m/%d}" for r in runs if len(r) == longest) +
                     f" ({longest}일, 징검다리 제외)",
                     "Longest: " + ", ".join(f"{r[0]:%b %d}–{r[-1]:%b %d}" for r in runs if len(r) == longest) +
                     f" ({longest} days, no extra days off)",
                     "El más largo: " + ", ".join(f"{r[0]:%d/%m}–{r[-1]:%d/%m}" for r in runs if len(r) == longest) +
                     f" ({longest} días, sin días puente)"),
                   T("긴 연휴엔 여행 사진도, 부스 사진도 한 번에",
                     "Long break = travel pics and booth pics",
                     "Puente largo = fotos de viaje y de cabina"), lo=3)
    qs.append(q2 if q2 is not None else q_long)

    if W is None:                               # 지역 '기타' — 날씨가 없으니 세 번째도 달력으로
        if q2 is not None:
            qs.append(q_long)
        else:
            qs.append(q_num("h3",
                            T(f"{NEXT}년 {nm['ko']}의 전국 공휴일은 며칠일까?",
                              f"How many national public holidays does {nm['en']} have in {NEXT}?",
                              f"¿Cuántos feriados nacionales tiene {nm['es']} en {NEXT}?"),
                            n_hol, DAYS, 1,
                            T(f"Nager.Date의 {NEXT}년 전국 공휴일 {n_hol}일",
                              f"Nager.Date national public holidays for {NEXT}: {n_hol}",
                              f"Feriados nacionales {NEXT} según Nager.Date: {n_hol}"),
                            T("공휴일 하루하루가 기념사진 찍을 핑계",
                              "Every holiday is an excuse for a photo",
                              "Cada feriado es una excusa para una foto")))
        return qs

    # 지난 10년, 연휴인데 비까지 온 날
    off_rain = 0
    for y in range(Y0, Y1 + 1):
        lw = {d for r in long_weekends(country, y) for d in r}
        off_rain += sum(1 for x in W if x["d"] in lw and x["rain"] >= RAIN_MM)
    per_year = off_rain / YEARS
    qs.append(q_num("h3",
                    T("연휴인데 비까지 오는 날은 1년에 며칠쯤일까?",
                      "How many long-weekend days a year turn out rainy?",
                      "¿Cuántos días de puente al año llueve?"),
                    per_year, DAYS, 1,
                    T(f"{Y0}~{Y1}년 3일 이상 연휴 가운데 강수 {RAIN_MM:g}mm 이상인 날, 1년 평균 {per_year:.1f}일",
                      f"Long-weekend days with ≥{RAIN_MM:g} mm rain, {Y0}–{Y1}: {per_year:.1f} a year",
                      f"Días de puente con ≥{RAIN_MM:g} mm de lluvia, {Y0}–{Y1}: {per_year:.1f} al año"),
                    T("쉬는 날인데 비? 그날이 바로 사진 찍는 날 📸",
                      "Day off and it's raining? That's your photo day 📸",
                      "¿Día libre y llueve? Ese es tu día de fotos 📸")))
    return qs


def golden_theme(W, nm):
    W25 = [x for x in W if x["d"].year == Y1]
    late = max(W25, key=lambda x: mins(x["sunset"]))
    # 가장 이른 일몰은 며칠 동안 같은 분으로 이어진다 — 그 첫날을 적는다
    early = min(W25, key=lambda x: (mins(x["sunset"]), x["d"]))
    diff = max(x["daylight"] for x in W25) - min(x["daylight"] for x in W25)
    a = mins(late["sunset"])
    opts = [hhmm(a - 70), hhmm(a), hhmm(a + 50)]
    e = mins(early["sunset"])
    e_opts = [hhmm(e - 45), hhmm(e), hhmm(e + 60)]
    qs = [
        q_pick("g1", "time",
               T(f"{nm['ko']}에서 1년 중 해가 가장 늦게 지는 시각은?",
                 f"In {nm['en']}, what's the latest sunset of the year?",
                 f"En {nm['es']}, ¿a qué hora es la puesta de sol más tardía del año?"),
               opts, hhmm(a),
               T(f"{Y1}년 일몰 시각(현지 시간) 중 가장 늦은 날은 {late['d']:%m월 %d일} {late['sunset']}",
                 f"Latest {Y1} sunset (local time): {late['d']:%b %d} at {late['sunset']}",
                 f"Puesta de sol más tardía de {Y1} (hora local): {late['d']:%d/%m} a las {late['sunset']}"),
               T("골든아워 사진은 이 시각 한 시간 전부터 🌅",
                 "Golden hour starts about an hour before this 🌅",
                 "La hora dorada empieza una hora antes 🌅")),
        q_pick("g2", "time",
               T("그럼 1년 중 해가 가장 일찍 지는 시각은?",
                 "And the earliest sunset of the year?",
                 "¿Y la puesta de sol más temprana del año?"),
               e_opts, hhmm(e),
               T(f"{Y1}년 일몰 시각(현지 시간) 중 가장 이른 날은 {early['d']:%m월 %d일} 무렵 {early['sunset']}",
                 f"Earliest {Y1} sunset (local time): around {early['d']:%b %d} at {early['sunset']}",
                 f"Puesta de sol más temprana de {Y1} (hora local): hacia el {early['d']:%d/%m} a las {early['sunset']}"),
               T("해가 가장 일찍 지는 날은 동지가 아니라 그보다 조금 앞서요. 저녁 약속은 실내로",
                 "The earliest sunset comes a bit before the shortest day. Evening plans? Go indoors",
                 "El atardecer más temprano llega antes del día más corto. ¿Planes de noche? Bajo techo")),
        q_num("g3",
              T("낮이 가장 긴 날과 가장 짧은 날, 낮 길이는 몇 시간 차이일까?",
                "How many more hours of daylight does the longest day have than the shortest?",
                "¿Cuántas horas más de luz tiene el día más largo que el más corto?"),
              diff, HOURS, 0.5 if diff < 3 else 1,
              T(f"{Y1}년 낮 길이(해 뜰 때부터 질 때까지) 최대 − 최소 = {diff:.1f}시간",
                f"{Y1} daylight, longest minus shortest day: {diff:.1f} hours",
                f"Luz del día en {Y1}, día más largo menos el más corto: {diff:.1f} horas"),
              T("겨울엔 해가 빨리 지니까 사진은 일찍, 혹은 실내에서",
                "Winter light goes fast — shoot early, or shoot inside",
                "En invierno la luz se va rápido: fotos temprano o bajo techo")),
    ]
    return [q for q in qs if q]


def cozy_theme(W, unit):
    u = "°F" if unit == "F" else "°C"
    lo = defaultdict(list)
    hi = defaultdict(list)
    for x in W:
        lo[x["d"].month].append(x["lo"])
        hi[x["d"].month].append(x["hi"])
    lo_m = {m: sum(v) / len(v) for m, v in lo.items()}
    hi_m = {m: sum(v) / len(v) for m, v in hi.items()}
    coldest = min(W, key=lambda x: x["lo"])
    spread = max(hi_m.values()) - min(hi_m.values())
    deg_u = T(u, u, u)
    return [
        q_month("c1",
                T("가장 추운 달은?", "Which month is the coldest?", "¿Cuál es el mes más frío?"),
                lo_m,
                T(f"{Y0}~{Y1}년 달별 아침 최저기온 평균: " +
                  " · ".join(f"{MON_KO[m-1]} {deg(lo_m[m], unit):.0f}{u}" for m in range(1, 13)),
                  f"Average daily low by month, {Y0}–{Y1}: " +
                  " · ".join(f"{dt.date(2000, m, 1):%b} {deg(lo_m[m], unit):.0f}{u}" for m in range(1, 13)),
                  f"Mínima media por mes, {Y0}–{Y1}: " +
                  " · ".join(f"{m}: {deg(lo_m[m], unit):.0f}{u}" for m in range(1, 13))),
                T("가장 추운 달엔 따뜻한 실내 데이트가 정답 🧣",
                  "Coldest month = cozy indoor date 🧣",
                  "Mes más frío = cita acogedora bajo techo 🧣"),
                best=min),
        q_num("c2",
              T(f"지난 10년, 가장 추웠던 날 아침 기온은?",
                "What was the coldest morning of the last 10 years?",
                "¿Cuál fue la mañana más fría de los últimos 10 años?"),
              deg(coldest["lo"], unit), deg_u, 3 if unit == "C" else 5,
              T(f"{Y0}~{Y1}년 하루 최저기온 중 가장 낮은 날: {coldest['d']:%Y-%m-%d} {deg(coldest['lo'], unit):.1f}{u}",
                f"Lowest daily low, {Y0}–{Y1}: {coldest['d']:%b %d, %Y} at {deg(coldest['lo'], unit):.1f}{u}",
                f"Mínima más baja, {Y0}–{Y1}: {coldest['d']:%d/%m/%Y} con {deg(coldest['lo'], unit):.1f}{u}"),
              T("기록적인 추위도 사진으로 남기면 추억",
                "Even a record cold snap makes a good memory",
                "Hasta el frío récord se vuelve un buen recuerdo"),
              lo=-100),
        q_num("c3",
              T("가장 더운 달과 가장 추운 달, 낮 기온은 몇 도 차이일까?",
                "How many degrees apart are the warmest and coldest months (daytime highs)?",
                "¿Cuántos grados de diferencia hay entre el mes más cálido y el más frío (máximas)?"),
              ddeg(spread, unit), deg_u, 2 if unit == "C" else 4,
              T(f"{Y0}~{Y1}년 달별 낮 최고기온 평균의 최대 − 최소 = {ddeg(spread, unit):.1f}{u}",
                f"Monthly average high, warmest minus coldest, {Y0}–{Y1}: {ddeg(spread, unit):.1f}{u}",
                f"Máxima media mensual, más cálido menos más frío, {Y0}–{Y1}: {ddeg(spread, unit):.1f}{u}"),
              T("계절이 바뀔 때마다 새 프레임으로 기록해 보세요",
                "New season, new frame",
                "Nueva estación, nuevo marco")),
    ]


def special_theme(W, unit):
    u = "°F" if unit == "F" else "°C"
    by_d = {x["d"]: x for x in W}

    def rainy_years(m, d):
        return sum(1 for y in range(Y0, Y1 + 1) if by_d[dt.date(y, m, d)]["rain"] >= RAIN_MM)

    xmas = rainy_years(12, 25)
    val = rainy_years(2, 14)
    hw = [by_d[dt.date(y, 10, 31)]["hi"] for y in range(Y0, Y1 + 1)]
    hw_avg = deg(sum(hw) / len(hw), unit)
    of10 = T("번 (10년 중)", " of 10 years", " de 10 años")
    return [
        q_num("d1",
              T("지난 10년, 크리스마스에 비가 온 해는 몇 번일까?",
                "In the last 10 years, how many Christmases were rainy?",
                "En los últimos 10 años, ¿cuántas Navidades llovió?"),
              xmas, of10, 2,
              T(f"{Y0}~{Y1}년 12월 25일 강수량 {RAIN_MM:g}mm 이상인 해: {xmas}번",
                f"Dec 25 with ≥{RAIN_MM:g} mm rain, {Y0}–{Y1}: {xmas} times",
                f"25 de diciembre con ≥{RAIN_MM:g} mm, {Y0}–{Y1}: {xmas} veces"),
              T("크리스마스 사진은 날씨 걱정 없는 실내에서 🎄",
                "Christmas photos: weather-proof indoors 🎄",
                "Fotos de Navidad: bajo techo, sin depender del clima 🎄"),
              lo=0, hi=10),
        q_num("d2",
              T("핼러윈(10월 31일) 낮 기온은 평균 몇 도일까?",
                "What's the average high on Halloween (Oct 31)?",
                "¿Cuál es la máxima media en Halloween (31 de octubre)?"),
              hw_avg, T(u, u, u), 3 if unit == "C" else 6,
              T(f"{Y0}~{Y1}년 10월 31일 낮 최고기온 평균 {hw_avg:.1f}{u}",
                f"Average Oct 31 high, {Y0}–{Y1}: {hw_avg:.1f}{u}",
                f"Máxima media del 31 de octubre, {Y0}–{Y1}: {hw_avg:.1f}{u}"),
              T("코스튬이 날씨에 맞는지 미리 체크 🎃",
                "Check if your costume fits the weather 🎃",
                "Revisa si tu disfraz va con el clima 🎃"),
              lo=-100),
        q_num("d3",
              T("지난 10년, 밸런타인데이에 비가 온 해는 몇 번일까?",
                "In the last 10 years, how many Valentine's Days were rainy?",
                "En los últimos 10 años, ¿cuántos San Valentín llovió?"),
              val, of10, 2,
              T(f"{Y0}~{Y1}년 2월 14일 강수량 {RAIN_MM:g}mm 이상인 해: {val}번",
                f"Feb 14 with ≥{RAIN_MM:g} mm rain, {Y0}–{Y1}: {val} times",
                f"14 de febrero con ≥{RAIN_MM:g} mm, {Y0}–{Y1}: {val} veces"),
              T("데이트 사진은 비가 와도 OK인 곳에서 💝",
                "Date photos? Pick a rain-proof spot 💝",
                "¿Fotos de cita? Elige un lugar a prueba de lluvia 💝"),
              lo=0, hi=10),
    ]


THEMES = [
    ("rainy", "☔", T("RAINY DAY", "RAINY DAY", "DÍA DE LLUVIA"),
     T("비 오는 날에 관한 호기심", "Curious facts about rainy days", "Curiosidades de los días de lluvia")),
    ("sunny", "☀️", T("SUNNY SEASON", "SUNNY SEASON", "TEMPORADA DE SOL"),
     T("맑고 따뜻한 날씨에 관한 호기심", "Clear skies and warm days", "Cielos despejados y días cálidos")),
    ("holiday", "🎉", T("HOLIDAY MOOD", "HOLIDAY MOOD", "MODO FERIADO"),
     T("연휴와 특별한 날에 관한 호기심", "Long weekends and days off", "Puentes y días libres")),
    ("golden", "🌅", T("GOLDEN HOUR", "GOLDEN HOUR", "HORA DORADA"),
     T("해 지는 시간에 관한 호기심", "When the sun goes down", "Cuándo se pone el sol")),
    ("cozy", "🧣", T("COZY SEASON", "COZY SEASON", "TEMPORADA ACOGEDORA"),
     T("추운 날에 관한 호기심", "Curious facts about cold days", "Curiosidades de los días fríos")),
    ("special", "💝", T("SPECIAL DAYS", "SPECIAL DAYS", "DÍAS ESPECIALES"),
     T("기념일 날씨에 관한 호기심", "Weather on the days that matter", "El clima en los días especiales")),
]

CAVEAT_W = T(
    "날씨는 매장 주변을 덮는 약 25km 격자의 ERA5 재분석 값이라 동네 관측소 기록과 다를 수 있습니다. "
    "특히 약한 비를 넓게 퍼뜨려서, 미국 매장 근처 관측소 4곳과 견주면 비 온 날이 1.2~1.5배 많게 나옵니다. "
    "비·더위는 실내 방문 수요를 짐작하는 대리 지표일 뿐, 실제 방문이나 매출을 잰 숫자가 아닙니다.",
    "Weather comes from ERA5 reanalysis on a ~25 km grid around the store, so it can differ from a local station. "
    "It spreads light rain widely: next to 4 stations near US stores it shows 1.2–1.5× as many rainy days. "
    "Rain and heat are only proxies for indoor demand, not measured visits or sales.",
    "El clima viene del reanálisis ERA5 en una cuadrícula de ~25 km, así que puede diferir de una estación local. "
    "Extiende la lluvia ligera: frente a 4 estaciones cerca de tiendas en EE. UU. muestra 1,2–1,5 veces más días de lluvia. "
    "La lluvia y el calor solo aproximan la demanda bajo techo; no miden visitas ni ventas.")
CAVEAT_H = {
    "US": T("공휴일은 Nager.Date의 연방 공휴일만 셉니다. 주마다 다른 공휴일과 개인 휴가는 빠집니다.",
            "Holidays are federal ones from Nager.Date; state holidays and personal days off are not included.",
            "Solo feriados federales de Nager.Date; no incluye feriados estatales ni días personales."),
    "KR": T("2016~2025년 공휴일은 Nager.Date의 오류(2008년에 빠진 제헌절, 빠진 대체·임시공휴일과 선거일)를 "
            "관공서 공휴일 규정과 발표된 임시공휴일로 바로잡아 셌습니다. 2026년부터는 Nager.Date 기준입니다.",
            "For 2016–2025, Nager.Date errors (Constitution Day after 2008, missing substitute, temporary and election "
            "holidays) were corrected from Korea's official holiday rules. From 2026 we use Nager.Date.",
            "Para 2016–2025 se corrigieron errores de Nager.Date (Día de la Constitución tras 2008, feriados "
            "sustitutos, temporales y electorales faltantes) con las reglas oficiales de Corea. Desde 2026 se usa Nager.Date."),
}


def main() -> None:
    regions, packs, months = [], {}, {}
    for rid, country, lat, lon, names in REGIONS:
        nm = dict(zip(("ko", "en", "es"), names))
        unit = "F" if country == "US" else "C"
        W = weather(rid, lat, lon)
        rq, rain_m = rainy_theme(W, nm)
        sq, clear_m = sunny_theme(W, nm, unit)
        th = {"rainy": rq, "sunny": sq, "holiday": holiday_theme(country, W),
              "golden": golden_theme(W, nm), "cozy": cozy_theme(W, unit),
              "special": special_theme(W, unit)}
        for k, qs in th.items():
            th[k] = [q for q in qs if q][:3]
            assert len(th[k]) == 3, f"{rid}/{k}: 문항이 {len(th[k])}개"
        packs[rid] = th
        months[rid] = {m: {"rain": round(rain_m[m], 1), "clear": round(clear_m[m], 1)}
                       for m in range(1, 13)}
        regions.append({"id": rid, "country": country, "name": T(*names), "unit": unit})
        print(f"{rid:11s} 비 오는 주말 {len(W) and sum(rain_m.values()):5.1f}일/년 · "
              f"맑은 주말 {sum(clear_m.values()):5.1f}일/년")

    for country in COUNTRY:
        rid = f"{country.lower()}-other"
        packs[rid] = {"holiday": holiday_theme(country, None)}
        regions.append({"id": rid, "country": country, "other": True,
                        "name": T("기타 지역", "Other area", "Otra zona"),
                        "unit": "F" if country == "US" else "C"})

    # 달 고르기 화면: 다가오는 달마다 연휴(3일 이상) 몇 번
    lw = {}
    for country in COUNTRY:
        cnt = Counter()
        for y in (NEXT - 1, NEXT):
            for r in long_weekends(country, y):
                cnt[f"{r[0]:%Y-%m}"] += 1
        lw[country] = dict(sorted(cnt.items()))

    out = {
        "updated": dt.date.today().isoformat(),
        "years": [Y0, Y1],
        "countries": {k: T(*v) for k, v in COUNTRY.items()},
        "regions": regions,
        "themes": [{"id": i, "emoji": e, "title": t, "blurb": b} for i, e, t, b in THEMES],
        "packs": packs,
        "months": months,
        "long_weekends": lw,
        "caveat": {"weather": CAVEAT_W, **{f"holiday_{k}": v for k, v in CAVEAT_H.items()}},
        "sources": [
            {"name": "Open-Meteo Archive (ERA5)", "url": "https://open-meteo.com/en/docs/historical-weather-api"},
            {"name": "Nager.Date", "url": "https://date.nager.at/"},
        ],
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"→ {OUT.name} ({OUT.stat().st_size // 1024}KB)")


if __name__ == "__main__":
    main()
