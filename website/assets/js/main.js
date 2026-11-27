(function () {
  'use strict';

  // 0. Lightweight OS Detection (for subtle recommendation on /download & hero button)
  const detectUserOS = function () {
    try {
      const ua = ((navigator.userAgentData && navigator.userAgentData.platform) || navigator.platform || navigator.userAgent || '').toLowerCase();
      if (ua.indexOf('win') !== -1) return 'windows';
      if (ua.indexOf('mac') !== -1) return 'mac';
      if (ua.indexOf('linux') !== -1 || ua.indexOf('x11') !== -1) return 'linux';
    } catch (_) {}
    return null;
  };

  try {
    const os = detectUserOS();
    const osCards = document.querySelectorAll('[data-os-card]');
    if (osCards.length) {
      const targetOS = os || 'windows';
      osCards.forEach(function (card) {
        const isMatch = card.getAttribute('data-os-card') === targetOS;
        card.classList.toggle('is-recommended', isMatch && Boolean(os));
        const cta = card.querySelector('.os-card-cta');
        if (cta) {
          cta.classList.toggle('btn-primary', isMatch);
          cta.classList.toggle('btn-surface', !isMatch);
        }
      });
    }

    const heroCta = document.getElementById('heroDownloadBtn');
    const heroCtaLabel = document.getElementById('heroDownloadLabel');
    if (heroCta && heroCtaLabel && os) {
      const osMap = {
        windows: { href: '/download/windows', label: 'Download for Windows' },
        mac: { href: '/download/mac', label: 'Download for macOS' },
        linux: { href: '/download/linux', label: 'Download for Linux' }
      };
      if (osMap[os]) {
        heroCta.setAttribute('href', osMap[os].href);
        heroCtaLabel.textContent = osMap[os].label;
      }
    }
  } catch (err) {
    console.error('OS hint init error:', err);
  }

  // 0b. Subtle 3D Cursor Tilt on ALL Screenshot Stages (Hero, /features, /davinci-resolve, /docs, /download/*)
  try {
    const motion = window.matchMedia('(prefers-reduced-motion: reduce)');
    const finePointer = window.matchMedia('(pointer: fine)');
    document.querySelectorAll('.tilt-stage').forEach(function (stage) {
      const isHero = stage.classList.contains('hero-showcase');
      const restX = isHero ? 1.5 : 0;
      const restY = isHero ? -2 : 0;
      let frame = 0;
      let tx = restX;
      let ty = restY;

      const paintTilt = function () {
        stage.style.setProperty('--tilt-x', tx.toFixed(2) + 'deg');
        stage.style.setProperty('--tilt-y', ty.toFixed(2) + 'deg');
        frame = 0;
      };

      stage.addEventListener('pointermove', function (e) {
        if (motion.matches || !finePointer.matches || window.innerWidth <= 760) return;
        const box = stage.getBoundingClientRect();
        if (!box.width || !box.height) return;
        tx = -(e.clientY - box.top - box.height / 2) / box.height * (isHero ? 3.2 : 4.2);
        ty = (e.clientX - box.left - box.width / 2) / box.width * (isHero ? 4.2 : 5.2);
        stage.classList.add('is-moving');
        if (!frame) frame = requestAnimationFrame(paintTilt);
      }, { passive: true });

      stage.addEventListener('pointerleave', function () {
        tx = restX;
        ty = restY;
        stage.classList.remove('is-moving');
        if (!frame) frame = requestAnimationFrame(paintTilt);
      }, { passive: true });
    });
  } catch (err) {
    console.error('Tilt stage init error:', err);
  }

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

  // 2. Interactive 5-Tab Feature Tour (Fast Text-Only Live Preview)
  try {
    const featureTabs = document.querySelectorAll('.feature-tab');
    const featureTitle = document.getElementById('featureTitle');
    const featureBadge = document.getElementById('featureBadge');
    const featureSummary = document.getElementById('featureSummary');
    const featureDemoLabel = document.getElementById('featureDemoLabel');
    const featureDemoBody = document.getElementById('featureDemoBody');
    const featureBullets = document.getElementById('featureBullets');
    const featureFootNote = document.getElementById('featureFootNote');
    const featureDeepLink = document.getElementById('featureDeepLink');

    if (featureTabs.length && featureTitle && featureDemoBody && featureBullets) {
      const makeSpan = function (cls, text) {
        const s = document.createElement('span');
        if (cls) s.className = cls;
        s.textContent = text;
        return s;
      };

      const renderDemoRows = function (rows) {
        featureDemoBody.innerHTML = '';
        rows.forEach(function (row) {
          const div = document.createElement('div');
          div.className = 'feature-demo-row';
          if (row.type === 'transcript') {
            const left = document.createElement('div');
            row.parts.forEach(function (p) {
              left.appendChild(makeSpan(p.cls, p.text));
            });
            div.appendChild(left);
            if (row.tag) div.appendChild(makeSpan('text-muted', row.tag));
          } else {
            div.appendChild(makeSpan('text-muted', row.label));
            div.appendChild(makeSpan(row.valCls || 'text-bright', row.value));
          }
          featureDemoBody.appendChild(div);
        });
      };

      const FEATURE_DATA = {
        verbatim: {
          title: 'True Verbatim Transcription',
          badge: 'Faster-Whisper & MLX',
          summary: 'Standard subtitles clean up speech and hide mistakes. BadWords preserves every stutter, false start, and filler word with word-level timestamps so nothing slips into the final cut.',
          demoLabel: 'Live Transcript Canvas Output',
          rows: [
            { type: 'transcript', parts: [
              { cls: 'text-muted', text: '[01:35]  ' },
              { cls: 'tok-retake', text: 'what do you... but where do you get a template...' }
            ], tag: 'Blue - Retake' },
            { type: 'transcript', parts: [
              { cls: 'text-muted', text: '[02:22]  It lives right here. ' },
              { cls: 'tok-cut', text: 'And remember this.' }
            ], tag: 'Red - Mistake' },
            { type: 'transcript', parts: [
              { cls: 'text-muted', text: '[02:26]  ...just type the ' },
              { cls: 'tok-keep', text: 'comment' },
              { cls: '', text: ' cat in front of that path.' }
            ], tag: 'Green - Deviation' }
          ],
          bullets: [
            'Catches every stutter, "um", and false start across ~100 spoken languages.',
            'Flags unintelligible audio as (...) for quick manual inspection.',
            'Word-level timestamps sync playback and DaVinci Resolve playhead jumps.'
          ],
          foot: 'Supports Large Turbo (default), Large v3, and Medium offline.',
          href: '/features#verbatim'
        },
        script: {
          title: 'Smart Script Comparison',
          badge: 'DNA-Inspired Alignment',
          summary: 'Import a .txt, .docx, or .pdf script and let BadWords align every spoken take against your intended lines - clean 1:1 takes stay untouched while mistakes pop out immediately.',
          demoLabel: 'Script vs Spoken Alignment',
          rows: [
            { type: 'kv', label: 'Script line', value: '"...just type cat in front of that path."', valCls: 'text-bright' },
            { type: 'kv', label: 'Spoken take #1', value: '"...type the comment cat in front..." (flagged)', valCls: 'text-emerald' },
            { type: 'kv', label: 'Hotword boost', value: 'Auto-extracted tech terms & names -> Whisper prompt', valCls: 'text-body' }
          ],
          bullets: [
            'Skips clean 1:1 scripted lines so you only review deviations and retakes.',
            'Extracts technical terms and brand names from your script to improve AI accuracy.',
            'Includes Side-by-Side Comparison View and script-free Standalone Analysis.'
          ],
          foot: 'Works with .txt, .docx, .pdf, or pasted clipboard scripts.',
          href: '/features#script'
        },
        silence: {
          title: 'Instant Silence & Fast Silence',
          badge: '<5 ms Live RAM Engine',
          summary: 'Auto-normalized audio loudness makes the default -42 dB threshold work out of the box across microphones, with live sliders that update cut regions in RAM without re-rendering.',
          demoLabel: 'Real-Time RAM Parameters',
          rows: [
            { type: 'kv', label: 'Auto-Norm Threshold', value: '-42.0 dB (consistent across mics)', valCls: 'text-emerald' },
            { type: 'kv', label: 'Island Absorption', value: 'Swallows desk bumps, breaths & coughs in pauses', valCls: 'text-bright' },
            { type: 'kv', label: 'Fast Silence Mode', value: 'Cuts full podcasts/gameplay in seconds (no AI)', valCls: 'text-body' }
          ],
          bullets: [
            'Tune silence threshold, pause removal %, min clip, and padding in under 5 ms.',
            'Bottom waveform player skips red and silence cuts live when you press Space.',
            'Switch to the Fast Silence tab when you only want dead air removed.'
          ],
          foot: 'Zero FFmpeg waiting while dragging silence sliders.',
          href: '/features#silence'
        },
        editor: {
          title: 'Standalone Mode & Multi-NLE',
          badge: 'XML / FCPXML / OTIO / EDL',
          summary: 'No DaVinci Resolve required. Drop MP4, MOV, MKV, or WAV files straight onto BadWords, cut by dragging across text or boxes, and export frame-accurate timelines to any editor.',
          demoLabel: 'Supported Input & Export Pipeline',
          rows: [
            { type: 'kv', label: 'Drop Queue', value: 'Multi-file video/audio + automatic 360p proxies', valCls: 'text-bright' },
            { type: 'kv', label: 'Selection Modes', value: 'Text Select (LMB), Marquee Box (RMB), Brush, Keys 1-4', valCls: 'text-body' },
            { type: 'kv', label: 'Timeline Formats', value: 'FCP7 XML, Apple FCPXML, OpenTimelineIO, CMX 3600 EDL', valCls: 'text-emerald' }
          ],
          bullets: [
            'Works independently on Windows, macOS, and Linux (Wayland & X11).',
            'Exact rational NTSC framerates (24000/1001, 30000/1001, 60000/1001) with zero drift.',
            'Project saves (.bws) include background autosave and crash recovery.'
          ],
          foot: 'Ready for DaVinci Resolve, Premiere Pro, Final Cut Pro & Kdenlive.',
          href: '/features#standalone'
        },
        assembly: {
          title: 'Assembly Panel & Heatmap',
          badge: 'Non-Destructive Rules',
          summary: 'Decide per marker color whether BadWords cuts a clip out automatically or keeps it as a colored timeline marker for manual timing tweaks inside DaVinci Resolve.',
          demoLabel: 'Per-Color Assembly Matrix',
          rows: [
            { type: 'kv', label: 'Red (Errors) & Silence', value: 'Auto-cut on Assemble (linked A/V clips)', valCls: 'text-rose' },
            { type: 'kv', label: 'Blue (Retakes) / Green (Typos)', value: 'Cut or keep as Resolve colored clip markers', valCls: 'text-sky' },
            { type: 'kv', label: 'Resolve Free 21.1+ & Studio', value: 'Lua Bridge + linked FCP7 XML or Studio .drt', valCls: 'text-emerald' }
          ],
          bullets: [
            'Creates a brand-new timeline copy so original footage and edits stay untouched.',
            'Timeline Heatmap lets you preserve comedic timing and inspect edge cases visually.',
            'Optional Studio .drt mode retains Color node grades, Fusion comps, and Fairlight FX.'
          ],
          foot: 'Custom color markers can also be pinned with dedicated shortcuts.',
          href: '/davinci-resolve'
        }
      };

      const renderFeature = function (key) {
        const data = FEATURE_DATA[key];
        if (!data) return;

        featureTitle.textContent = data.title;
        if (featureBadge) featureBadge.textContent = data.badge;
        if (featureSummary) featureSummary.textContent = data.summary;
        if (featureDemoLabel) featureDemoLabel.textContent = data.demoLabel;
        renderDemoRows(data.rows);
        if (featureFootNote) featureFootNote.textContent = data.foot;
        if (featureDeepLink) featureDeepLink.setAttribute('href', data.href);

        featureBullets.innerHTML = '';
        data.bullets.forEach(function (text) {
          const li = document.createElement('li');
          const dot = document.createElement('span');
          dot.className = 'bullet-dot';
          const span = document.createElement('span');
          span.textContent = text;
          li.appendChild(dot);
          li.appendChild(span);
          featureBullets.appendChild(li);
        });

        featureTabs.forEach(function (btn) {
          const active = btn.getAttribute('data-feature-tab') === key;
          btn.classList.toggle('is-active', active);
          btn.setAttribute('aria-selected', String(active));
        });
      };

      featureTabs.forEach(function (btn) {
        btn.addEventListener('click', function () {
          renderFeature(btn.getAttribute('data-feature-tab'));
        });
      });
    }
  } catch (err) {
    console.error('Feature showcase error:', err);
  }

  // 3. Clipboard Copy Button on Download Pages
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

  // 4. Fullscreen Lightbox Modal
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

  // 5. Changelog Version Group Filter
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

  // 6. Docs Search + Match Counter + Active TOC Highlighter
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
