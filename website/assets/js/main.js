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

  // 2. Smooth 3D Pointer Tilt on Showcase Windows (No Glow / No Shadow)
  try {
    const motionReduced = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const finePointer = !window.matchMedia || window.matchMedia('(pointer: fine)').matches;

    if (!motionReduced && finePointer) {
      document.querySelectorAll('.tilt-stage').forEach(function (stage) {
        let rafId = 0;
        let tiltX = 0.8;
        let tiltY = -1.0;

        const paint = function () {
          stage.style.setProperty('--tilt-x', tiltX.toFixed(2) + 'deg');
          stage.style.setProperty('--tilt-y', tiltY.toFixed(2) + 'deg');
          rafId = 0;
        };

        stage.addEventListener('pointermove', function (e) {
          if (window.innerWidth <= 768) return;
          const rect = stage.getBoundingClientRect();
          tiltX = -((e.clientY - rect.top - rect.height / 2) / rect.height) * 3.5;
          tiltY = ((e.clientX - rect.left - rect.width / 2) / rect.width) * 4.5;
          stage.classList.add('is-moving');
          if (!rafId) rafId = window.requestAnimationFrame(paint);
        }, { passive: true });

        stage.addEventListener('pointerleave', function () {
          tiltX = 0.8;
          tiltY = -1.0;
          stage.classList.remove('is-moving');
          if (!rafId) rafId = window.requestAnimationFrame(paint);
        }, { passive: true });
      });
    }
  } catch (err) {
    console.error('Tilt init error:', err);
  }

  // 3. Interactive 5-Tab Feature Tour (Home Page)
  try {
    const featureTabs = document.querySelectorAll('.feature-tab');
    const featureTitle = document.getElementById('featureTitle');
    const featurePreviewImg = document.getElementById('featurePreviewImg');
    const featureLightboxBtn = document.getElementById('featureLightboxBtn');
    const featureBullets = document.getElementById('featureBullets');
    const assemblySubToggle = document.getElementById('assemblySubToggle');
    const assemblySubtabs = document.querySelectorAll('.assembly-subtab');

    if (featureTabs.length && featureTitle && featurePreviewImg && featureBullets) {
      const FEATURE_DATA = {
        verbatim: {
          title: 'True Verbatim Transcription',
          src: '/assets/img/hero-workspace.webp',
          alt: 'BadWords v4.1.2 desktop editor displaying verbatim transcript, silence sliders, and cut regions',
          caption: 'True Verbatim Transcription - Every word, stutter, and silence live on one screen',
          bullets: [
            'Faster-Whisper & Apple MLX tuned to preserve stutters, "ums", and false starts instead of hiding mistakes.',
            'Marks unintelligible mumbling as (...) and lets you audition every edit by pressing Space.',
            'Streams word-level timestamps in ~100 languages completely offline on your GPU or CPU.'
          ]
        },
        script: {
          title: 'Smart Script Comparison',
          src: '/assets/img/feature-script-diff.webp',
          alt: 'BadWords v4.1.2 Script Comparison panel comparing pasted text against spoken dialogue',
          caption: 'Smart Script Comparison - Highlight only deviations from your script',
          bullets: [
            'DNA-inspired alignment skips clean 1:1 takes and isolates off-script lines or repeated takes.',
            'Extracts technical terms, acronyms, and brand names from .txt, .docx, and .pdf files before transcription.',
            'Includes Side-by-Side Comparison View and Standalone Auto-Analyze for unscripted recordings.'
          ]
        },
        silence: {
          title: 'Instant Silence & Fast Silence',
          src: '/assets/img/feature-fast-silence.webp',
          alt: 'BadWords v4.1.2 Silence Detection tab with real-time dB sliders and waveform cut regions',
          caption: 'Fast Silence & Waveform - Instant in-RAM recalculation under 5 ms',
          bullets: [
            'Automatic loudness normalization keeps the -42 dB threshold reliable across quiet or loud mics.',
            'Island absorption merges tiny coughs or desk bumps back into silence cuts automatically.',
            'Adjust threshold, pause ratio, and padding live in RAM - or cut pauses without transcribing via Fast Silence.'
          ]
        },
        editor: {
          title: 'Standalone Mode & Multi-NLE Export',
          src: '/assets/img/feature-welcome-standalone.webp',
          alt: 'BadWords v4.1.2 Standalone File Mode welcome workspace with multi-file drop zone',
          caption: 'Standalone Mode - Work directly from local video/audio files without Resolve',
          bullets: [
            'Drop MP4, MOV, MKV, or WAV files directly from disk with smooth background 360p preview proxies.',
            'Edit visually via Notepad text selection, Marquee drag box, or brush keys 1-4.',
            'Export frame-accurate cut timelines to FCP7 XML, Apple FCPXML, OpenTimelineIO (.otio), or CMX 3600 EDL.'
          ]
        },
        assembly: {
          title: 'Assembly Panel & Timeline Heatmap',
          views: {
            panel: {
              src: '/assets/img/feature-assembly.webp',
              alt: 'BadWords v4.1.2 Assembly Options panel showing per-color cut and marker toggles',
              caption: 'Assembly Panel - Per-color cut or timeline marker rules'
            },
            heatmap: {
              src: '/assets/img/heatmap-preview.webp',
              alt: 'DaVinci Resolve timeline heatmap with linked color-coded clips generated by BadWords',
              caption: 'Resolve Timeline Heatmap - Non-destructive linked clips with markers'
            }
          },
          bullets: [
            'Choose per marker color whether BadWords cuts a clip or leaves colored Resolve markers as an editing heatmap.',
            'Exact drop-frame timing (23.976 / 29.97 / 59.94 fps) with linked FCP7 XML default or Studio .drt preservation.',
            'Every Assemble generates a brand-new timeline copy so your original sequence and source files are untouched.'
          ]
        }
      };

      let currentAssemblyView = 'panel';

      const setMedia = function (src, alt, caption) {
        featurePreviewImg.src = src;
        featurePreviewImg.alt = alt;
        if (featureLightboxBtn) {
          featureLightboxBtn.setAttribute('data-lightbox-src', src);
          featureLightboxBtn.setAttribute('data-lightbox-caption', caption);
        }
      };

      const renderFeature = function (key) {
        const data = FEATURE_DATA[key];
        if (!data) return;

        featureTitle.textContent = data.title;
        if (key === 'assembly' && data.views) {
          if (assemblySubToggle) assemblySubToggle.classList.remove('hidden');
          const v = data.views[currentAssemblyView] || data.views.panel;
          setMedia(v.src, v.alt, v.caption);
        } else {
          if (assemblySubToggle) assemblySubToggle.classList.add('hidden');
          setMedia(data.src, data.alt, data.caption);
        }

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

      assemblySubtabs.forEach(function (btn) {
        btn.addEventListener('click', function () {
          currentAssemblyView = btn.getAttribute('data-assembly-view') || 'panel';
          assemblySubtabs.forEach(function (sub) {
            const active = sub === btn;
            sub.classList.toggle('is-active', active);
            sub.setAttribute('aria-selected', String(active));
          });
          renderFeature('assembly');
        });
      });
    }
  } catch (err) {
    console.error('Feature showcase error:', err);
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

  // 7. Docs Search + Match Counter + Active TOC Highlighter
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
