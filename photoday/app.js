/* PHOTO DAY — 언어 · 지역 · 테마 · 3문항 · 달 고르기 · 샘플 쿠폰
 *
 * 숫자는 전부 photobox.json 에 미리 계산돼 있다 (tools/build_photobox.py).
 * 이 화면은 보여 주고 채점만 한다. 서버를 부르지 않는다.
 */

const $ = (id) => document.getElementById(id);
const VIEWS = ["home", "themes", "quiz", "result", "coupon"];

let D = null;          // photobox.json
let LANG = "ko";
let REGION = null;     // 고른 지역
let THEME = null;      // 고른 테마
let QS = [];
let idx = 0;
let hits = 0;
let MONTH = null;      // "2027-03"

/* ── 문구 ──────────────────────────────────────────── */
const I18N = {
  ko: {
    heroTitle: "내 사진 찍는 날 찾기",
    heroLead: "퀴즈 3문항 · 30초 · 끝나면 쿠폰 🎟️",
    step1: "STEP 1 · 어느 매장에 자주 가세요?",
    step2: "STEP 2 · 궁금한 테마를 골라 주세요",
    otherNote: "기타 지역은 날씨를 셀 매장이 없어서 공휴일 테마만 열려요",
    locked: "매장 지역을 고르면 열려요",
    backThemes: "← 테마 고르기",
    count: (i, n) => `${i} / ${n}`,
    next: "다음",
    seeResult: "결과 보기",
    hit: "정답! 📸",
    miss: "아깝다!",
    answerIs: (a) => `정답은 ${a}`,
    basis: "근거 보기",
    score: (h, n) => `${n}문항 중 ${h}개 맞혔어요`,
    step3: "STEP 3 · 사진 찍으러 올 달을 골라요",
    step3Lead: "고른 달 한 달 동안 쓸 수 있는 쿠폰을 드려요",
    rainy: (n) => `☔ 비 오는 주말 평균 ${n}일`,
    lw: (n) => `🎉 연휴 ${n}번`,
    noLw: "연휴 없음",
    tagRain: "실내 추천",
    tagHoliday: "연휴 있음",
    dayLabel: "날짜도 정할래요 (선택)",
    getCoupon: "쿠폰 받기",
    moreThemes: "다른 테마 풀기",
    limits: "이 데이터의 한계",
    source: "출처",
    couponFor: "PHOTO DAY 쿠폰",
    off: "10% OFF",
    when: (m) => `${m} 한 달 동안`,
    stackable: "다른 할인과 중복 사용 가능",
    showCode: "매장에서 이 코드를 보여 주세요",
    addCal: "캘린더에 추가",
    share: "친구에게 보내기",
    copied: "링크를 복사했어요",
    sampleNote: "시제품용 샘플 쿠폰입니다. 실제 매장에서는 사용할 수 없어요.",
    shared: (p, t) => `친구가 ${t}에서 ${p}! 당신은요?`,
    calTitle: "📸 PHOTO DAY — 사진 찍는 날",
    seasons: { spring: "봄", summer: "여름", fall: "가을", winter: "겨울" },
    personas: [
      ["🌈", "즉흥 사진가"],
      ["☂️", "우산 챙기는 타입"],
      ["📸", "감 좋은 포토러버"],
      ["🎯", "날씨 촉 만렙"],
    ],
  },
  en: {
    heroTitle: "Find your photo day",
    heroLead: "3 questions · 30 seconds · a coupon at the end 🎟️",
    step1: "STEP 1 · Where do you usually visit us?",
    step2: "STEP 2 · Pick a theme",
    otherNote: "For other areas we can't count local weather, so only the holiday theme is open",
    locked: "Pick a store area to unlock",
    backThemes: "← Themes",
    count: (i, n) => `${i} / ${n}`,
    next: "Next",
    seeResult: "See result",
    hit: "Nailed it! 📸",
    miss: "So close!",
    answerIs: (a) => `The answer is ${a}`,
    basis: "How we counted",
    score: (h, n) => `You got ${h} of ${n}`,
    step3: "STEP 3 · Pick your photo month",
    step3Lead: "Your coupon works all month long",
    rainy: (n) => `☔ avg ${n} rainy weekend days`,
    lw: (n) => `🎉 ${n} long weekend${n > 1 ? "s" : ""}`,
    noLw: "No long weekend",
    tagRain: "Indoor pick",
    tagHoliday: "Long weekend",
    dayLabel: "Pick a date too (optional)",
    getCoupon: "Get my coupon",
    moreThemes: "Try another theme",
    limits: "Data limits",
    source: "Source",
    couponFor: "PHOTO DAY COUPON",
    off: "10% OFF",
    when: (m) => `Valid all of ${m}`,
    stackable: "Stackable with other offers",
    showCode: "Show this code in store",
    addCal: "Add to calendar",
    share: "Send to a friend",
    copied: "Link copied",
    sampleNote: "Sample coupon for a prototype. Not valid in stores.",
    shared: (p, t) => `Your friend is a ${p} on ${t}. Your turn!`,
    calTitle: "📸 PHOTO DAY",
    seasons: { spring: "Spring", summer: "Summer", fall: "Fall", winter: "Winter" },
    personas: [
      ["🌈", "Spontaneous Snapper"],
      ["☂️", "Umbrella Packer"],
      ["📸", "Sharp-Eyed Snapper"],
      ["🎯", "Weather Whisperer"],
    ],
  },
  es: {
    heroTitle: "Encuentra tu día de fotos",
    heroLead: "3 preguntas · 30 segundos · cupón al final 🎟️",
    step1: "PASO 1 · ¿Qué tienda visitas más?",
    step2: "PASO 2 · Elige un tema",
    otherNote: "En otras zonas no medimos el clima local, así que solo está el tema de feriados",
    locked: "Elige una tienda para abrirlo",
    backThemes: "← Temas",
    count: (i, n) => `${i} / ${n}`,
    next: "Siguiente",
    seeResult: "Ver resultado",
    hit: "¡Correcto! 📸",
    miss: "¡Casi!",
    answerIs: (a) => `La respuesta es ${a}`,
    basis: "Cómo lo contamos",
    score: (h, n) => `Acertaste ${h} de ${n}`,
    step3: "PASO 3 · Elige tu mes de fotos",
    step3Lead: "Tu cupón vale todo ese mes",
    rainy: (n) => `☔ prom. ${n} días de finde con lluvia`,
    lw: (n) => `🎉 ${n} puente${n > 1 ? "s" : ""}`,
    noLw: "Sin puentes",
    tagRain: "Ideal bajo techo",
    tagHoliday: "Con puente",
    dayLabel: "Elige también un día (opcional)",
    getCoupon: "Obtener cupón",
    moreThemes: "Probar otro tema",
    limits: "Límites de los datos",
    source: "Fuente",
    couponFor: "CUPÓN PHOTO DAY",
    off: "10% DE DESCUENTO",
    when: (m) => `Válido todo ${m}`,
    stackable: "Acumulable con otras ofertas",
    showCode: "Muestra este código en la tienda",
    addCal: "Agregar al calendario",
    share: "Enviar a un amigo",
    copied: "Enlace copiado",
    sampleNote: "Cupón de muestra de un prototipo. No válido en tiendas.",
    shared: (p, t) => `Tu amigo es ${p} en ${t}. ¡Te toca!`,
    calTitle: "📸 PHOTO DAY",
    seasons: { spring: "Primavera", summer: "Verano", fall: "Otoño", winter: "Invierno" },
    personas: [
      ["🌈", "Espíritu espontáneo"],
      ["☂️", "Siempre con paraguas"],
      ["📸", "Ojo de fotógrafo"],
      ["🎯", "Experto del clima"],
    ],
  },
};
const LANGS = [["ko", "한국어"], ["en", "English"], ["es", "Español"]];
const CODE = {
  la: "LAK", pleasanton: "PLS", milpitas: "MLP", honolulu: "HNL", carrollton: "CRT",
  frisco: "FRS", annarbor: "ANA", seoul: "SEL", busan: "PUS", "us-other": "USA", "kr-other": "KOR",
};
const FLAG = { US: "🇺🇸", KR: "🇰🇷" };
const L = () => I18N[LANG];
const tr = (o) => (o && typeof o === "object" ? o[LANG] ?? o.en : o);

/* 저장소가 막힌 브라우저(시크릿 창 등)에서도 앱은 그대로 돈다 */
function remember(k, v) { try { localStorage.setItem(k, v); } catch { /* 무시 */ } }
function recall(k) { try { return localStorage.getItem(k); } catch { return null; } }

function show(name) {
  VIEWS.forEach((v) => ($(`view-${v}`).hidden = v !== name));
  window.scrollTo({ top: 0 });
}

function flash() {
  const f = $("flash");
  f.classList.remove("on");
  void f.offsetWidth;          // 애니메이션을 처음부터 다시
  f.classList.add("on");
}

/* ── 보기 문구 ───────────────────────────────────────── */
function monthName(m, year) {
  const d = new Date(year ?? 2000, m - 1, 1);
  return new Intl.DateTimeFormat(LANG, year ? { month: "long", year: "numeric" } : { month: "long" }).format(d);
}
function timeName(s) {
  const [h, m] = s.split(":").map(Number);
  return new Intl.DateTimeFormat(LANG, { hour: "numeric", minute: "2-digit" })
    .format(new Date(2000, 0, 1, h, m));
}
function optLabel(q, o) {
  if (q.kind === "month") return monthName(o);
  if (q.kind === "season") return L().seasons[o];
  if (q.kind === "time") return timeName(o);
  return `${o}${tr(q.unit)}`;
}

/* ── 언어 ───────────────────────────────────────────── */
function setLang(l) {
  LANG = I18N[l] ? l : "en";
  remember("photoday-lang", LANG);
  document.documentElement.lang = LANG;
  document.querySelectorAll("[data-t]").forEach((el) => {
    const v = L()[el.dataset.t];
    if (typeof v === "string") el.textContent = v;
  });
  $("lang").innerHTML = "";
  LANGS.forEach(([k, name]) => {
    const b = document.createElement("button");
    b.textContent = name;
    b.setAttribute("aria-pressed", String(k === LANG));
    b.onclick = () => { setLang(k); rerender(); };
    $("lang").appendChild(b);
  });
}

/* 언어를 바꾸면 지금 보고 있는 화면을 그 언어로 다시 그린다 */
function rerender() {
  renderRegions();
  if (REGION) renderThemes();
  if (!$("view-quiz").hidden) renderQ(!$("reveal").hidden);
  if (!$("view-result").hidden) renderResult(false);
  if (!$("view-coupon").hidden) renderCoupon();
}

/* ── 1. 지역 ────────────────────────────────────────── */
function renderRegions() {
  const box = $("regions");
  box.innerHTML = "";
  Object.keys(D.countries).forEach((c) => {
    const g = document.createElement("div");
    g.className = "country";
    g.innerHTML = `<p class="cname">${FLAG[c]} ${tr(D.countries[c])}</p>`;
    const row = document.createElement("div");
    row.className = "chips";
    D.regions.filter((r) => r.country === c).forEach((r) => {
      const b = document.createElement("button");
      b.className = "chip" + (r.other ? " other" : "");
      b.textContent = tr(r.name);
      b.onclick = () => pickRegion(r.id);
      row.appendChild(b);
    });
    g.appendChild(row);
    box.appendChild(g);
  });
}

function pickRegion(id) {
  REGION = D.regions.find((r) => r.id === id);
  if (!REGION) return;
  renderThemes();
  show("themes");
}

/* ── 2. 테마 ────────────────────────────────────────── */
function renderThemes() {
  $("btn-region").textContent = `← ${FLAG[REGION.country]} ${tr(REGION.name)}`;
  const pack = D.packs[REGION.id];
  $("other-note").hidden = !REGION.other;
  $("themes").innerHTML = "";
  D.themes.forEach((t, i) => {
    const open = !!pack[t.id];
    const b = document.createElement("button");
    b.className = `tcard th-${t.id}` + (open ? "" : " locked");
    b.style.animationDelay = `${i * 50}ms`;
    b.disabled = !open;
    b.innerHTML =
      `<span class="tnum">0${i + 1}</span>` +
      `<span class="temoji">${t.emoji}</span>` +
      `<span class="ttitle">${tr(t.title)}</span>` +
      `<span class="tblurb">${open ? tr(t.blurb) : L().locked}</span>`;
    b.onclick = () => start(t.id);
    $("themes").appendChild(b);
  });
}

/* ── 3. 문항 ────────────────────────────────────────── */
function start(themeId) {
  THEME = D.themes.find((t) => t.id === themeId);
  // 고른 답을 문항에 적어 두므로, 원본을 건드리지 않게 복사해서 쓴다
  QS = structuredClone(D.packs[REGION.id][themeId]);
  idx = 0; hits = 0;
  renderQ(false);
  show("quiz");
}

function renderFilm() {
  $("film").innerHTML = QS.map((q, i) => {
    const cls = i < idx ? (q.got ? "hit" : "miss") : i === idx ? "now" : "";
    const mark = i < idx ? (q.got ? "✓" : "✕") : i + 1;
    return `<span class="${cls}">${mark}</span>`;
  }).join("");
}

function renderQ(revealed) {
  const q = QS[idx];
  renderFilm();
  $("q-count").textContent = `${THEME.emoji} ${tr(THEME.title)} · ${L().count(idx + 1, QS.length)}`;
  $("q-text").textContent = tr(q.text);
  $("q-options").innerHTML = "";
  q.options.forEach((o) => {
    const b = document.createElement("button");
    b.className = "choice";
    b.type = "button";
    b.textContent = optLabel(q, o);
    b.dataset.v = String(o);
    b.onclick = () => answer(o);
    $("q-options").appendChild(b);
  });
  $("reveal").hidden = true;
  $("btn-next").hidden = true;
  if (revealed) paintReveal(q.mine);
}

function answer(o) {
  const q = QS[idx];
  if (q.locked) return;
  q.locked = true;
  q.mine = o;
  q.got = String(o) === String(q.answer);
  if (q.got) hits++;
  flash();
  paintReveal(o);
}

function paintReveal(mine) {
  const q = QS[idx];
  [...$("q-options").children].forEach((b) => {
    b.disabled = true;
    if (b.dataset.v === String(q.answer)) b.classList.add("real");
    else if (b.dataset.v === String(mine)) b.classList.add("wrong");
  });
  $("reveal").innerHTML =
    `<p class="verdict ${q.got ? "hit" : "miss"}">${q.got ? L().hit : L().miss}` +
    (q.got ? "" : ` <span>${L().answerIs(optLabel(q, q.answer))}</span>`) + `</p>` +
    `<p class="why">${tr(q.why)}</p>` +
    `<details><summary>${L().basis}</summary><p class="basis">${tr(q.basis)}</p></details>`;
  $("reveal").hidden = false;
  $("btn-next").textContent = idx === QS.length - 1 ? L().seeResult : L().next;
  $("btn-next").hidden = false;
}

function next() {
  if (idx < QS.length - 1) { idx++; renderQ(false); return; }
  idx = QS.length;
  MONTH = null;
  renderResult(true);
  show("result");
}

/* ── 4. 결과 + 달 고르기 ─────────────────────────────── */
function upcomingMonths() {
  // 다음 달부터 여섯 달. 연휴 데이터가 있는 해까지만
  const now = new Date();
  const lw = D.long_weekends[REGION.country];
  const lastYear = Math.max(...Object.keys(lw).map((k) => +k.slice(0, 4)));
  const out = [];
  for (let i = 1; out.length < 6; i++) {
    const d = new Date(now.getFullYear(), now.getMonth() + i, 1);
    if (d.getFullYear() > lastYear) break;
    out.push({ y: d.getFullYear(), m: d.getMonth() + 1 });
  }
  return out;
}

function renderResult(fresh) {
  const [emoji, name] = L().personas[Math.min(hits, 3)];
  $("persona-emoji").textContent = emoji;
  $("persona").textContent = name;
  $("score").textContent = L().score(hits, QS.length);
  if (fresh) $("view-result").querySelector(".polaroid").classList.add("develop");

  const stats = D.months[REGION.id];        // 기타 지역은 날씨가 없다
  const lw = D.long_weekends[REGION.country];
  const list = upcomingMonths();
  const top = stats ? Math.max(...list.map(({ m }) => stats[m].rain)) : -1;

  $("months").innerHTML = "";
  list.forEach(({ y, m }) => {
    const key = `${y}-${String(m).padStart(2, "0")}`;
    const n = lw[key] || 0;
    const s = stats && stats[m];
    const tags = [];
    if (s && s.rain === top && top > 0) tags.push(`<em class="tag rain">${L().tagRain}</em>`);
    if (n) tags.push(`<em class="tag hol">${L().tagHoliday}</em>`);
    const b = document.createElement("button");
    b.className = "month" + (key === MONTH ? " on" : "");
    b.setAttribute("aria-pressed", String(key === MONTH));
    b.innerHTML =
      `<span class="mname">${monthName(m, y)}</span>` +
      `<span class="mtags">${tags.join("")}</span>` +
      (s ? `<span class="mstat">${L().rainy(s.rain)}</span>` : "") +
      `<span class="mstat">${n ? L().lw(n) : L().noLw}</span>`;
    b.onclick = () => pickMonth(key, y, m);
    $("months").appendChild(b);
  });
  $("btn-coupon").disabled = !MONTH;
  $("day-wrap").hidden = !MONTH;

  const cav = [];
  if (stats) cav.push(tr(D.caveat.weather));
  cav.push(tr(D.caveat[`holiday_${REGION.country}`]));
  $("caveat").textContent = cav.join(" ");
  $("source").innerHTML = `${L().source} ` + D.sources
    .map((s) => `<a href="${s.url}" target="_blank" rel="noopener">${s.name}</a>`).join(" · ");
}

function pickMonth(key, y, m) {
  MONTH = key;
  const last = new Date(y, m, 0).getDate();
  const day = $("day");
  day.min = `${key}-01`;
  day.max = `${key}-${String(last).padStart(2, "0")}`;
  if (day.value && !day.value.startsWith(key)) day.value = "";
  renderResult(false);
}

/* ── 5. 쿠폰 ────────────────────────────────────────── */
function couponCode() {
  return `PD-${CODE[REGION.id] || "XXX"}-${MONTH.slice(2, 4)}${MONTH.slice(5, 7)}`;
}

function renderCoupon() {
  const [y, m] = MONTH.split("-").map(Number);
  $("c-off").textContent = L().off;
  $("c-when").textContent = L().when(monthName(m, y));
  $("c-code").textContent = couponCode();
}

/* 캘린더 파일(.ics) — 날짜를 골랐으면 그날, 아니면 그 달 1일에 알림 */
function addCalendar() {
  const day = $("day").value || `${MONTH}-01`;
  const d0 = day.replaceAll("-", "");
  const d1 = new Date(day + "T00:00:00");
  d1.setDate(d1.getDate() + 1);
  const end = `${d1.getFullYear()}${String(d1.getMonth() + 1).padStart(2, "0")}${String(d1.getDate()).padStart(2, "0")}`;
  const ics = [
    "BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//photo-day//EN", "BEGIN:VEVENT",
    `UID:${d0}-${couponCode()}@photo-day`,
    `DTSTAMP:${new Date().toISOString().replace(/[-:]/g, "").slice(0, 15)}Z`,
    `DTSTART;VALUE=DATE:${d0}`, `DTEND;VALUE=DATE:${end}`,
    `SUMMARY:${L().calTitle}`,
    `DESCRIPTION:${tr(REGION.name)} · ${couponCode()} (SAMPLE)`,
    "END:VEVENT", "END:VCALENDAR",
  ].join("\r\n");
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([ics], { type: "text/calendar" }));
  a.download = "photo-day.ics";
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}

async function share() {
  const [, name] = L().personas[Math.min(hits, 3)];
  const url = `${location.origin}${location.pathname}?lang=${LANG}` +
    `&r=${encodeURIComponent(REGION.id)}&t=${encodeURIComponent(THEME.id)}&p=${Math.min(hits, 3)}`;
  const text = `PHOTO DAY · ${tr(THEME.title)} · ${name}`;
  try {
    if (navigator.share) { await navigator.share({ title: "PHOTO DAY", text, url }); return; }
    await navigator.clipboard.writeText(`${text}\n${url}`);
    $("btn-share").textContent = L().copied;
    setTimeout(() => ($("btn-share").textContent = L().share), 1800);
  } catch { /* 사용자가 취소한 경우 */ }
}

/* ── 시작 ───────────────────────────────────────────── */
async function boot() {
  D = await (await fetch("photobox.json")).json();
  const p = new URLSearchParams(location.search);
  const guess = (navigator.language || "en").slice(0, 2);
  setLang(p.get("lang") || recall("photoday-lang") || (I18N[guess] ? guess : "en"));
  renderRegions();

  $("btn-region").onclick = () => show("home");
  $("btn-back").onclick = () => { renderThemes(); show("themes"); };
  $("btn-next").onclick = next;
  $("btn-more").onclick = () => { renderThemes(); show("themes"); };
  $("btn-again").onclick = () => { renderThemes(); show("themes"); };
  $("btn-coupon").onclick = () => { renderCoupon(); show("coupon"); flash(); };
  $("btn-cal").onclick = addCalendar;
  $("btn-share").onclick = share;

  // 친구가 보낸 링크: 지역·테마를 미리 고른 채로 연다
  if (p.has("r") && D.regions.some((r) => r.id === p.get("r"))) {
    pickRegion(p.get("r"));
    const t = D.themes.find((x) => x.id === p.get("t"));
    if (t && p.has("p")) {
      const [emoji, name] = L().personas[Math.min(+p.get("p") || 0, 3)];
      $("shared-banner").textContent = `${emoji} ` + L().shared(name, tr(t.title));
      $("shared-banner").hidden = false;
      show("home");
    } else if (t && D.packs[REGION.id][t.id]) {
      start(t.id);
    }
  }
}

boot();
