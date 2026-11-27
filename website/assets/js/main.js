(function () {
  'use strict';

  // 1. Mobile Navigation Toggle
  try {
    const btn = document.getElementById('mobileMenuBtn');
    const panel = document.getElementById('mobileMenuPanel');
    const iconOpen = document.getElementById('menuIconOpen');
    const iconClose = document.getElementById('menuIconClose');

    if (btn && panel) {
      const setOpen = function (open) {
        panel.classList.toggle('hidden', !open);
        if (iconOpen) iconOpen.classList.toggle('hidden', open);
        if (iconClose) iconClose.classList.toggle('hidden', !open);
        btn.setAttribute('aria-expanded', String(open));
      };

      btn.addEventListener('click', function () {
        setOpen(panel.classList.contains('hidden'));
      });

      document.querySelectorAll('.mobile-link').forEach(function (el) {
        el.addEventListener('click', function () { setOpen(false); });
      });
    }
  } catch (err) {
    console.error('Mobile nav init error:', err);
  }

  // 2. Pleofon-Style Frameless 3D Pointer Tilt on Showcase Windows
  try {
    const motionReduced = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const finePointer = !window.matchMedia || window.matchMedia('(pointer: fine)').matches;

    if (!motionReduced && finePointer) {
      document.querySelectorAll('.tilt-stage').forEach(function (stage) {
        let rafId = 0;
        let tiltX = 1.2;
        let tiltY = -1.4;

        const paint = function () {
          stage.style.setProperty('--tilt-x', tiltX.toFixed(2) + 'deg');
          stage.style.setProperty('--tilt-y', tiltY.toFixed(2) + 'deg');
          rafId = 0;
        };

        stage.addEventListener('pointermove', function (e) {
          if (window.innerWidth <= 768) return;
          const rect = stage.getBoundingClientRect();
          tiltX = -((e.clientY - rect.top - rect.height / 2) / rect.height) * 4.0;
          tiltY = ((e.clientX - rect.left - rect.width / 2) / rect.width) * 5.0;
          stage.classList.add('is-moving');
          if (!rafId) rafId = window.requestAnimationFrame(paint);
        }, { passive: true });

        stage.addEventListener('pointerleave', function () {
          tiltX = 1.2;
          tiltY = -1.4;
          stage.classList.remove('is-moving');
          if (!rafId) rafId = window.requestAnimationFrame(paint);
        }, { passive: true });
      });
    }
  } catch (err) {
    console.error('Tilt init error:', err);
  }

  // 3. Home Interactive 4-Step Live Rough Cut Demo (StoryCraft-inspired)
  try {
    const stepBtns = document.querySelectorAll('.demo-step');
    const stageLabel = document.getElementById('demoStageLabel');
    const stageBody = document.getElementById('demoTranscript');
    const stageMetricLeft = document.getElementById('demoMetricLeft');
    const stageMetricRight = document.getElementById('demoMetricRight');
    const pauseBtn = document.getElementById('demoPauseBtn');

    if (stepBtns.length && stageBody && stageMetricLeft && stageMetricRight) {
      const SCENES = [
        {
          label: 'Step 01 - Local Faster-Whisper / MLX',
          metricLeft: 'Processing locally on GPU - 0 bytes uploaded',
          metricRight: 'Verbatim words + timestamps captured',
          lines: [
            { t: '00:00', html: 'Um, hey everyone, welcome back to the channel.' },
            { t: '00:04', html: 'Today we are gonna... Today I am showing you how to automate rough cuts.' },
            { t: '00:13', html: '<span class="tok-sil">[ silence 1.6s ]</span> Uh, wait, let me restart that.' },
            { t: '00:18', html: 'Everything runs offline on your hardware and exports linked XML.' }
          ]
        },
        {
          label: 'Step 02 - Mistakes, Retakes & Silences Flagged',
          metricLeft: 'Red: 2 fillers  |  Blue: 1 retake  |  Silences: -42 dB',
          metricRight: '18:40 raw -> 11:05 after auto-cuts',
          lines: [
            { t: '00:00', html: '<span class="tok-red">Um,</span> hey everyone, welcome back to the channel.' },
            { t: '00:04', html: '<span class="tok-blue">Today we are gonna...</span> Today I am showing you how to automate rough cuts.' },
            { t: '00:13', html: '<span class="tok-sil">-1.6s cut</span> <span class="tok-red">Uh, wait, let me restart that.</span>' },
            { t: '00:18', html: 'Everything runs offline on your hardware and exports <span class="tok-green">linked</span> XML.' }
          ]
        },
        {
          label: 'Step 03 - Edit Text & Tune Silence Live (<5 ms)',
          metricLeft: 'Keep pause: 0.10s  |  Pauses removed: 90%',
          metricRight: 'Spacebar skips cuts live in playback',
          lines: [
            { t: '00:00', html: '<span class="tok-red">Um,</span> hey everyone, welcome back to the channel.' },
            { t: '00:04', html: '<span class="tok-blue">Today we are gonna...</span> Today I am showing you how to automate rough cuts.' },
            { t: '00:13', html: '<span class="tok-sil">keep 0.10s</span> <span class="tok-red">Uh, wait, let me restart that.</span>' },
            { t: '00:18', html: 'Everything runs offline on your hardware and exports linked XML.' }
          ]
        },
        {
          label: 'Step 04 - New Non-Destructive Timeline Ready',
          metricLeft: 'DaVinci Resolve (Free 21.1+ / Studio) or Premiere / FCP',
          metricRight: 'Source media untouched - linked A/V clips',
          lines: [
            { t: '00:00', html: 'Hey everyone, welcome back to the channel.' },
            { t: '00:02', html: 'Today I am showing you how to automate rough cuts.' },
            { t: '00:05', html: 'Everything runs offline on your hardware and exports linked XML.' },
            { t: '00:09', html: '<strong class="text-emerald">Assembled: Podcast_EP42_BadWords_Cut (.xml / Resolve Timeline)</strong>' }
          ]
        }
      ];

      let activeIdx = 0;
      let paused = false;
      let elapsedMs = 0;
      const STEP_MS = 4500;

      const renderScene = function (idx) {
        activeIdx = idx;
        elapsedMs = 0;
        const sc = SCENES[idx];
        if (stageLabel) stageLabel.textContent = sc.label;
        stageMetricLeft.textContent = sc.metricLeft;
        stageMetricRight.textContent = sc.metricRight;

        stageBody.innerHTML = '';
        sc.lines.forEach(function (line) {
          const row = document.createElement('div');
          row.className = 'demo-line';
          const tm = document.createElement('span');
          tm.className = 'demo-time';
          tm.textContent = '[' + line.t + ']';
          const txt = document.createElement('span');
          txt.innerHTML = line.html;
          row.appendChild(tm);
          row.appendChild(txt);
          stageBody.appendChild(row);
        });

        stepBtns.forEach(function (btn, i) {
          const isAct = i === idx;
          btn.classList.toggle('is-active', isAct);
          btn.setAttribute('aria-selected', String(isAct));
          const bar = btn.querySelector('.demo-progress');
          if (bar) bar.style.width = '0%';
        });
      };

      stepBtns.forEach(function (btn, i) {
        btn.addEventListener('click', function () {
          renderScene(i);
        });
      });

      if (pauseBtn) {
        pauseBtn.addEventListener('click', function () {
          paused = !paused;
          pauseBtn.textContent = paused ? 'Play' : 'Pause';
          pauseBtn.setAttribute('aria-pressed', String(paused));
        });
      }

      renderScene(0);
      window.setInterval(function () {
        if (paused) return;
        elapsedMs += 100;
        const activeBtn = stepBtns[activeIdx];
        if (activeBtn) {
          const bar = activeBtn.querySelector('.demo-progress');
          if (bar) bar.style.width = Math.min(100, (elapsedMs / STEP_MS) * 100).toFixed(1) + '%';
        }
        if (elapsedMs >= STEP_MS) {
          renderScene((activeIdx + 1) % SCENES.length);
        }
      }, 100);
    }
  } catch (err) {
    console.error('Demo showcase error:', err);
  }

  // 4. Clipboard Copy Button on Download Pages
  try {
    const osCommand = document.getElementById('osCommand');
    const copyBtn = document.getElementById('copyCommandBtn');
    if (copyBtn && osCommand) {
      let resetTimer = null;
      copyBtn.addEventListener('click', async function () {
        const text = osCommand.textContent.trim();
        try {
          if (navigator.clipboard && navigator.clipboard.writeText) {
            await navigator.clipboard.writeText(text);
          } else {
            const ta = document.createElement('textarea');
            ta.value = text;
            ta.style.position = 'fixed';
            ta.style.opacity = '0';
            document.body.appendChild(ta);
            ta.select();
            document.execCommand('copy');
            document.body.removeChild(ta);
          }
          copyBtn.textContent = 'Copied!';
          copyBtn.classList.add('is-copied');
          if (resetTimer) clearTimeout(resetTimer);
          resetTimer = setTimeout(function () {
            copyBtn.textContent = 'Copy';
            copyBtn.classList.remove('is-copied');
          }, 2000);
        } catch (err) {
          console.error('Copy failed:', err);
        }
      });
    }
  } catch (err) {
    console.error('Copy button error:', err);
  }

  // 5. Fullscreen Lightbox Modal
  try {
    const modal = document.getElementById('lightboxModal');
    const modalImg = document.getElementById('lightboxImg');
    const modalCaption = document.getElementById('lightboxCaption');
    const closeBtn = document.getElementById('lightboxCloseBtn');
    let lastTrigger = null;

    if (modal && modalImg && modalCaption) {
      const openModal = function (src, caption, triggerEl) {
        lastTrigger = triggerEl || null;
        modalImg.src = src;
        modalImg.alt = caption || 'BadWords screenshot preview';
        modalCaption.textContent = caption || '';
        modal.classList.add('is-open');
        document.body.style.overflow = 'hidden';
        if (closeBtn) closeBtn.focus();
      };

      const closeModal = function () {
        modal.classList.remove('is-open');
        modalImg.src = '';
        document.body.style.overflow = '';
        if (lastTrigger && typeof lastTrigger.focus === 'function') {
          lastTrigger.focus();
        }
      };

      document.querySelectorAll('.lightbox-trigger').forEach(function (trigger) {
        trigger.addEventListener('click', function () {
          const src = trigger.getAttribute('data-lightbox-src');
          const caption = trigger.getAttribute('data-lightbox-caption') || '';
          if (src) openModal(src, caption, trigger);
        });
      });

      if (closeBtn) closeBtn.addEventListener('click', closeModal);
      modal.addEventListener('click', function (e) {
        if (e.target === modal) closeModal();
      });
      document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape' && modal.classList.contains('is-open')) {
          closeModal();
        }
      });
    }
  } catch (err) {
    console.error('Lightbox error:', err);
  }

  // 6. Changelog Version Group Filter
  try {
    const filterBtns = document.querySelectorAll('[data-changelog-filter]');
    const releaseCards = document.querySelectorAll('[data-release-major]');
    if (filterBtns.length && releaseCards.length) {
      filterBtns.forEach(function (btn) {
        btn.addEventListener('click', function () {
          const val = btn.getAttribute('data-changelog-filter');
          filterBtns.forEach(function (b) { b.classList.toggle('is-active', b === btn); });
          releaseCards.forEach(function (card) {
            const maj = card.getAttribute('data-release-major');
            const show = val === 'all' || val === maj || (val === 'older' && (maj === '2' || maj === '1'));
            card.classList.toggle('hidden', !show);
          });
        });
      });
    }
  } catch (err) {
    console.error('Changelog filter error:', err);
  }

  // 7. Enhanced Docs Search + Match Counter + Active TOC Highlighter
  try {
    const searchInput = document.getElementById('docsSearchInput');
    const clearBtn = document.getElementById('docsSearchClear');
    const metaEl = document.getElementById('docsSearchMeta');
    const emptyState = document.getElementById('docsEmptyState');
    const sections = document.querySelectorAll('.docs-article section');
    const navLinks = document.querySelectorAll('.docs-nav a');

    if (searchInput && sections.length) {
      const applyFilter = function () {
        const q = searchInput.value.trim().toLowerCase();
        if (clearBtn) clearBtn.classList.toggle('hidden', !q);
        let visibleCount = 0;

        sections.forEach(function (sec) {
          const id = sec.getAttribute('id');
          const keywords = (sec.getAttribute('data-keywords') || '').toLowerCase();
          const match = !q || sec.textContent.toLowerCase().indexOf(q) !== -1 || keywords.indexOf(q) !== -1;
          sec.classList.toggle('hidden', !match);
          if (match) visibleCount++;
          navLinks.forEach(function (link) {
            if (link.getAttribute('href') === '#' + id) {
              link.classList.toggle('hidden', !match);
            }
          });
        });

        if (metaEl) {
          metaEl.textContent = q
            ? (visibleCount + ' of ' + sections.length + ' sections match "' + searchInput.value.trim() + '"')
            : ('All ' + sections.length + ' sections - press / to search');
        }
        if (emptyState) {
          emptyState.classList.toggle('hidden', visibleCount > 0);
        }
      };

      searchInput.addEventListener('input', applyFilter);
      if (clearBtn) {
        clearBtn.addEventListener('click', function () {
          searchInput.value = '';
          applyFilter();
          searchInput.focus();
        });
      }

      document.addEventListener('keydown', function (e) {
        if (e.key === '/' && document.activeElement !== searchInput && !e.ctrlKey && !e.metaKey) {
          e.preventDefault();
          searchInput.focus();
        }
      });
    }

    if (navLinks.length && sections.length && 'IntersectionObserver' in window) {
      const observer = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            const id = entry.target.getAttribute('id');
            navLinks.forEach(function (link) {
              link.classList.toggle('is-active', link.getAttribute('href') === '#' + id);
            });
          }
        });
      }, { rootMargin: '-18% 0px -70% 0px' });

      sections.forEach(function (sec) { observer.observe(sec); });
    }
  } catch (err) {
    console.error('Docs helper error:', err);
  }
})();
