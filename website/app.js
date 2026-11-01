// StoryCraft site: the workflow stepper and the install tabs. No libraries, no tracking.
(function () {
  "use strict";

  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const SCENE_MS = 6000; // each step plays this long before the next one

  // ── Waveform bars (scene 1) ──
  const wave = document.querySelector("[data-wave]");
  if (wave) {
    let seed = 7;
    const rand = () => (seed = (seed * 9301 + 49297) % 233280) / 233280;
    for (let i = 0; i < 72; i++) {
      const bar = document.createElement("i");
      const speech = Math.sin(i / 5) * 0.35 + 0.55;
      const spike = i === 30 || i === 31 ? 1 : 0; // the loud sound
      bar.style.height = Math.round(8 + (spike ? 56 : speech * 44 * (0.45 + rand() * 0.55))) + "%";
      if (spike) bar.style.background = "#8b5a3c";
      wave.insertBefore(bar, wave.firstChild);
    }
  }

  // ── Stepper ──
  const stage = document.querySelector(".stage");
  const steps = Array.from(document.querySelectorAll(".step"));
  const scenes = Array.from(document.querySelectorAll(".scene"));
  const pauseBtn = document.querySelector(".stage-pause");
  const howGrid = document.querySelector(".how-grid");
  if (!stage || !steps.length) return;

  let current = 0;
  let timers = [];
  let playing = !reduced;
  let visible = false;

  const clearTimers = () => { timers.forEach(clearTimeout); timers = []; };

  function countUp(el, ms) {
    const start = performance.now();
    const tick = (now) => {
      const p = Math.min(1, (now - start) / ms);
      el.textContent = Math.round(p * 100);
      if (p < 1 && el.isConnected && el.closest(".scene.active")) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  }

  function resetScene(scene) {
    scene.classList.add("resetting"); // back to the start at once, without fading out
    scene.querySelectorAll("[data-at]").forEach((el) => {
      el.classList.remove(el.dataset.cls || "on");
      if (el.dataset.cls === "count") el.textContent = "0";
    });
    void scene.offsetWidth;
    scene.classList.remove("resetting");
  }

  function apply(el, instant) {
    const cls = el.dataset.cls || "on";
    if (cls === "count") {
      if (instant) el.textContent = "100"; else countUp(el, 4000);
      return;
    }
    el.classList.add(cls);
  }

  function restartProgress(btn) {
    const bar = btn.querySelector(".step-progress");
    if (!bar) return;
    bar.style.animation = "none";
    void bar.offsetWidth; // restart the CSS animation
    bar.style.animation = "";
  }

  function show(i, { auto = playing } = {}) {
    clearTimers();
    current = (i + steps.length) % steps.length;
    steps.forEach((b, k) => b.setAttribute("aria-selected", String(k === current)));
    scenes.forEach((s, k) => s.classList.toggle("active", k === current));
    const scene = scenes[current];
    resetScene(scene);
    void scene.offsetWidth;
    const items = Array.from(scene.querySelectorAll("[data-at]"));
    if (!auto) {
      items.forEach((el) => apply(el, true)); // a still picture of the step, finished
      howGrid.classList.add("paused");
      return;
    }
    howGrid.classList.remove("paused");
    howGrid.style.setProperty("--dur", SCENE_MS + "ms");
    restartProgress(steps[current]);
    items.forEach((el) => timers.push(setTimeout(() => apply(el, false), Number(el.dataset.at) || 0)));
    timers.push(setTimeout(() => show(current + 1), SCENE_MS));
  }

  function setPlaying(on) {
    playing = on && !reduced;
    pauseBtn.textContent = playing ? "Pause" : "Play";
    pauseBtn.setAttribute("aria-label", playing ? "Pause the animation" : "Play the animation");
    show(current, { auto: playing && visible });
  }

  steps.forEach((btn, k) => btn.addEventListener("click", () => show(k, { auto: playing && visible })));
  steps.forEach((btn) => btn.addEventListener("keydown", (e) => {
    if (e.key !== "ArrowDown" && e.key !== "ArrowUp" && e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
    e.preventDefault();
    const next = current + (e.key === "ArrowDown" || e.key === "ArrowRight" ? 1 : -1);
    show(next, { auto: playing && visible });
    steps[current].focus();
  }));
  pauseBtn.addEventListener("click", () => setPlaying(!playing));
  if (reduced) pauseBtn.hidden = true;

  // Only play while the stage is on screen
  if ("IntersectionObserver" in window) {
    new IntersectionObserver((entries) => {
      const now = entries[entries.length - 1].isIntersecting;
      if (now === visible) return;
      visible = now;
      if (visible) show(current, { auto: playing });
      else clearTimers();
    }, { threshold: 0.35 }).observe(stage);
  } else {
    visible = true;
  }
  // ?step=N opens on a step (1-4), e.g. to link to one
  const asked = Number(new URLSearchParams(location.search).get("step"));
  if (asked >= 1 && asked <= steps.length) current = asked - 1;
  show(current, { auto: false });

  // ── Screenshot gallery ──
  const CAPTIONS = {
    "clean-up": "Clean up: fillers, repeats and a loud cough found and marked; the inspector shows what the AI found and what each colour does in Resolve.",
    "story-board": "Compose: the story board with its blocks and target length, next to the transcript and the player.",
    "start": "Start: pick the timeline or a file, the language and the model, then Analyze.",
    "settings": "Settings: one calm page per topic, with the StoryCraft and StoryCraft Light themes.",
  };
  const LIGHT_NAMES = { "settings": "settings-light" };
  // Raise after replacing any file in assets/shots so browsers drop their cached copy.
  const SHOTS_V = "2";
  const shotImg = document.getElementById("shot-img");
  const shotCap = document.getElementById("shot-caption");
  const shotTabs = Array.from(document.querySelectorAll("[data-shot]"));
  const modeTabs = Array.from(document.querySelectorAll("[data-mode]"));
  let shot = "clean-up", mode = "dark";
  const shotSrc = () => {
    if (mode === "light") return "assets/shots/" + (LIGHT_NAMES[shot] || shot + "-light") + ".jpg?v=" + SHOTS_V;
    return "assets/shots/" + shot + ".jpg?v=" + SHOTS_V;
  };
  const showShot = () => {
    shotTabs.forEach((b) => b.setAttribute("aria-selected", String(b.dataset.shot === shot)));
    modeTabs.forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.mode === mode)));
    const src = shotSrc();
    if (shotImg && shotImg.getAttribute("src") !== src) {
      shotImg.classList.add("loading");
      shotImg.onload = () => shotImg.classList.remove("loading");
      shotImg.src = src;
    }
    if (shotCap) shotCap.textContent = CAPTIONS[shot];
  };
  shotTabs.forEach((b) => b.addEventListener("click", () => { shot = b.dataset.shot; showShot(); }));
  modeTabs.forEach((b) => b.addEventListener("click", () => { mode = b.dataset.mode; showShot(); }));
  const box = document.getElementById("lightbox");
  const boxImg = document.getElementById("lightbox-img");
  const opener = document.querySelector(".shot-open");
  if (opener && box && typeof box.showModal === "function") {
    opener.addEventListener("click", () => {
      boxImg.src = shotImg.src;
      boxImg.alt = shotImg.alt;
      box.showModal();
    });
    box.addEventListener("click", (e) => { if (e.target === box) box.close(); });
  }

  // ── Install tabs and copy buttons ──
  const tabs = Array.from(document.querySelectorAll(".tab[data-os]"));
  const cmds = Array.from(document.querySelectorAll(".cmd"));
  const pick = (os) => {
    tabs.forEach((t) => t.setAttribute("aria-selected", String(t.dataset.os === os)));
    cmds.forEach((c) => { c.hidden = c.dataset.os !== os; });
  };
  tabs.forEach((t) => t.addEventListener("click", () => pick(t.dataset.os)));
  const ua = navigator.userAgent;
  pick(/Windows/.test(ua) ? "win" : /Linux/.test(ua) && !/Android/.test(ua) ? "linux" : "mac");

  document.querySelectorAll(".copy").forEach((btn) => btn.addEventListener("click", async () => {
    const text = btn.parentElement.querySelector("code").textContent;
    try {
      await navigator.clipboard.writeText(text);
      btn.textContent = "Copied";
    } catch (e) {
      const range = document.createRange();
      range.selectNodeContents(btn.parentElement.querySelector("code"));
      const sel = window.getSelection();
      sel.removeAllRanges();
      sel.addRange(range);
      btn.textContent = "Selected";
    }
    setTimeout(() => { btn.textContent = "Copy"; }, 1600);
  }));
})();
