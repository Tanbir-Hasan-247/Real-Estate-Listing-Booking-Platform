/**
 * PropNest Real Estate — Interactive, WebGL & Scroll Engine
 */
import * as THREE from 'three';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
import { ShaderPass } from 'three/addons/postprocessing/ShaderPass.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { HDRLoader } from 'three/addons/loaders/HDRLoader.js';
import { MeshoptDecoder } from 'three/addons/libs/meshopt_decoder.module.js';

(() => {
  'use strict';

  const g2 = document.getElementById('top');
  if (!g2) return;

  const PN_CFG = window.PROPNEST_CONFIG || {};
  let HOME_DATA = null;
  const homeDataEl = document.getElementById('propnest-home-data');
  if (homeDataEl) {
    try {
      HOME_DATA = JSON.parse(homeDataEl.textContent || '{}');
    } catch (e) {
      HOME_DATA = null;
    }
  }
  const prefersReducedMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches || false;

  const cursorRing = g2.querySelector('[data-g2-cursor="ring"]');
  const cursorDot = g2.querySelector('[data-g2-cursor="dot"]');
  const header = g2.querySelector('header');
  const menuDialog = document.getElementById('g2-main-menu');

  const heroSection = g2.querySelector('[data-g2-section="hero"]');
  const marqueeSection = g2.querySelector('[data-g2-section="marquee"]');
  const storySection = g2.querySelector('[data-g2-section="story"]');
  const portfolioSection = document.getElementById('portfolio');
  const locationsSection = document.getElementById('locations');
  const towerSection = g2.querySelector('[data-g2-section="tower"]');
  const amenitiesSection = document.getElementById('amenities');
  const interiorsSection = document.getElementById('interiors');
  const emblemSection = g2.querySelector('[data-g2-section="emblem"]');
  const dayNightWrapper = g2.querySelector('[data-g2-section="daynight"]');
  const ctaSection = g2.querySelector('[data-g2-section="cta"]');
  const footerSection = g2.querySelector('[data-g2-section="footer"]');

  [ctaSection, footerSection].forEach(el => {
    if (el) el.classList.remove('g2-offscreen');
  });

  // Pause CSS keyframes on marquee / spin elements while scrolled offscreen
  const marqueeContainers = Array.from(g2.querySelectorAll('[data-g2-section="marquee"], .g2-clients'));
  if ('IntersectionObserver' in window && marqueeContainers.length) {
    const offscreenObserver = new IntersectionObserver(
      entries => {
        entries.forEach(entry => {
          entry.target.classList.toggle('g2-offscreen', !entry.isIntersecting);
        });
      },
      { rootMargin: '120px 0px' }
    );
    marqueeContainers.forEach(el => offscreenObserver.observe(el));
  } else {
    marqueeContainers.forEach(el => el.classList.remove('g2-offscreen'));
  }

  const clamp01 = v => Math.min(1, Math.max(0, v));
  const range01 = (v, a, b) => clamp01((v - a) / (b - a));
  const easeInOutQuad = t => (t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2);

  // =========================================================================
  // 1. CUSTOM CURSOR (RING + DOT) — Idle-Paused On Demand
  // =========================================================================
  if (!prefersReducedMotion && window.matchMedia('(pointer: fine)').matches && cursorRing && cursorDot) {
    let mouseX = -100;
    let mouseY = -100;
    let ringX = -100;
    let ringY = -100;
    let cursorVisible = false;
    let lastTarget = null;
    let lastHideCustom = null;
    let lastOnInteractive = null;
    let cursorRafId = 0;

    const tickCursor = () => {
      cursorRafId = 0;
      if (!cursorVisible) return;
      const dx = mouseX - ringX;
      const dy = mouseY - ringY;
      if (Math.abs(dx) <= 0.15 && Math.abs(dy) <= 0.15) {
        ringX = mouseX;
        ringY = mouseY;
        cursorRing.style.transform = `translate3d(${ringX}px, ${ringY}px, 0) translate(-50%, -50%)`;
        return;
      }
      ringX += dx * 0.18;
      ringY += dy * 0.18;
      cursorRing.style.transform = `translate3d(${ringX.toFixed(1)}px, ${ringY.toFixed(1)}px, 0) translate(-50%, -50%)`;
      cursorRafId = requestAnimationFrame(tickCursor);
    };

    const ensureCursorTick = () => {
      if (!cursorRafId && cursorVisible) {
        cursorRafId = requestAnimationFrame(tickCursor);
      }
    };

    window.addEventListener('mousemove', e => {
      mouseX = e.clientX;
      mouseY = e.clientY;
      if (!cursorVisible) {
        ringX = mouseX;
        ringY = mouseY;
        cursorVisible = true;
        cursorRing.style.opacity = '1';
        cursorDot.style.opacity = '1';
        cursorRing.style.transform = `translate3d(${ringX}px, ${ringY}px, 0) translate(-50%, -50%)`;
      }
      cursorDot.style.transform = `translate3d(${mouseX}px, ${mouseY}px, 0) translate(-50%, -50%)`;

      if (e.target && e.target !== lastTarget) {
        lastTarget = e.target;
        const hideCustom = Boolean(
          e.target.closest?.('dialog, input, select, textarea, option, iframe, [data-native-cursor]')
        );
        if (hideCustom !== lastHideCustom) {
          lastHideCustom = hideCustom;
          cursorRing.style.visibility = hideCustom ? 'hidden' : 'visible';
          cursorDot.style.visibility = hideCustom ? 'hidden' : 'visible';
        }
        const onInteractive = Boolean(
          e.target.closest?.("a, button, [role='button'], input, select, textarea, label, summary")
        );
        if (onInteractive !== lastOnInteractive) {
          lastOnInteractive = onInteractive;
          cursorRing.style.width = onInteractive ? '64px' : '40px';
          cursorRing.style.height = onInteractive ? '64px' : '40px';
          cursorRing.style.backgroundColor = onInteractive
            ? 'color-mix(in srgb, var(--g2-gold) 12%, transparent)'
            : 'transparent';
        }
      }
      ensureCursorTick();
    }, { passive: true });

    document.addEventListener('mouseleave', () => {
      cursorVisible = false;
      cursorRing.style.opacity = '0';
      cursorDot.style.opacity = '0';
      if (cursorRafId) {
        cancelAnimationFrame(cursorRafId);
        cursorRafId = 0;
      }
    });
    document.addEventListener('mouseenter', () => {
      if (mouseX >= 0 && mouseY >= 0) {
        cursorVisible = true;
        cursorRing.style.opacity = '1';
        cursorDot.style.opacity = '1';
      }
    });
  }

  // =========================================================================
  // 2. HEADER BLUR, DARK/LIGHT THEME TOGGLE & MENU DRAWER
  // =========================================================================
  const headerBlur = header ? header.querySelector('[data-g2-header-blur]') : null;
  const themeBtn = header ? header.querySelector('button[aria-label*="mode"]') : null;
  const menuBtn = header ? header.querySelector('button[aria-label*="menu"]') : null;

  let towerController = null;
  let menuController = null;
  let menuInitStarted = false;

  const THEME_STORAGE_KEY = 'propnest-theme';
  const colorSchemeMeta = document.querySelector('meta[name="color-scheme"]');
  const osDarkMq = window.matchMedia?.('(prefers-color-scheme: dark)');

  function resolveInitialTheme() {
    try {
      const saved = localStorage.getItem(THEME_STORAGE_KEY);
      if (saved === 'light' || saved === 'dark') return saved;
    } catch (_) {}
    return g2.getAttribute('data-g2-theme') || (osDarkMq?.matches === false ? 'light' : 'dark');
  }

  function applyTheme(next, persist = false) {
    g2.setAttribute('data-g2-theme', next);
    document.body.style.background = next === 'dark' ? 'rgb(13, 58, 94)' : 'rgb(255, 255, 255)';
    document.body.style.color = next === 'dark' ? 'rgb(244, 236, 225)' : 'rgb(23, 27, 44)';

    if (colorSchemeMeta) {
      if (persist) {
        const osTheme = osDarkMq?.matches === false ? 'light' : 'dark';
        colorSchemeMeta.content = next === osTheme ? 'light dark' : next;
      } else {
        try {
          const saved = localStorage.getItem(THEME_STORAGE_KEY);
          colorSchemeMeta.content = saved === 'light' || saved === 'dark' ? saved : 'light dark';
        } catch (_) {}
      }
    }

    if (persist) {
      try {
        const osTheme = osDarkMq?.matches === false ? 'light' : 'dark';
        if (next === osTheme) localStorage.removeItem(THEME_STORAGE_KEY);
        else localStorage.setItem(THEME_STORAGE_KEY, next);
      } catch (_) {}
    }

    if (themeBtn) {
      themeBtn.setAttribute('aria-label', next === 'dark' ? 'Switch to light mode' : 'Switch to dark mode');
      const labelSpan = themeBtn.querySelector('.g2-nav');
      if (labelSpan) labelSpan.textContent = next;
      const knob = themeBtn.querySelector('span > span.rounded-full');
      if (knob) {
        knob.style.transition = 'transform 300ms cubic-bezier(0.16, 1, 0.3, 1)';
        knob.style.transform = next === 'dark' ? 'translateX(22px)' : 'translateX(0px)';
      }
    }
    if (towerController) towerController.setTheme(next);
  }

  applyTheme(resolveInitialTheme(), false);

  if (themeBtn) {
    themeBtn.addEventListener('click', () => {
      const current = g2.getAttribute('data-g2-theme') || 'dark';
      const next = current === 'dark' ? 'light' : 'dark';
      applyTheme(next, true);
    });
  }

  window.addEventListener('storage', e => {
    if (e.key === THEME_STORAGE_KEY) {
      applyTheme(e.newValue === 'light' || e.newValue === 'dark' ? e.newValue : (osDarkMq?.matches === false ? 'light' : 'dark'), false);
    }
  });

  let menuOpen = false;
  const menuAboutBtn = document.getElementById('g2-menu-about-btn');
  const menuBackBtn = document.getElementById('g2-menu-back-btn');
  const menuPrimary = document.getElementById('g2-menu-primary');
  const menuSubmenu = document.getElementById('g2-menu-submenu');

  function setMenuOpen(open) {
    menuOpen = open;
    if (!menuDialog || !menuBtn) return;
    menuDialog.setAttribute('aria-hidden', open ? 'false' : 'true');
    menuBtn.setAttribute('aria-expanded', open ? 'true' : 'false');
    menuBtn.setAttribute('aria-label', open ? 'Close menu' : 'Open menu');

    const label = menuBtn.querySelector('.g2-nav');
    if (label) label.textContent = open ? 'Close' : 'Menu';

    const bars = menuBtn.querySelectorAll('span.relative > span');
    if (bars.length === 2) {
      bars[0].style.transition = 'transform 350ms cubic-bezier(0.16, 1, 0.3, 1)';
      bars[1].style.transition = 'transform 350ms cubic-bezier(0.16, 1, 0.3, 1)';
      bars[0].style.transform = open ? 'translateY(4.5px) rotate(45deg)' : 'none';
      bars[1].style.transform = open ? 'translateY(-4.5px) rotate(-45deg)' : 'none';
    }

    if (!open && menuPrimary && menuSubmenu) {
      menuPrimary.classList.remove('hidden');
      menuSubmenu.classList.add('hidden');
    }
    if (!menuDialog.hasAttribute('inert') && !open) menuDialog.setAttribute('inert', '');
    if (open) {
      menuDialog.removeAttribute('inert');
      if (!menuController && typeof ensureMenuController === 'function') {
        ensureMenuController();
      }
    }
    if (menuController) menuController.setOpen(open);
  }

  if (menuBtn) {
    menuBtn.addEventListener('pointerenter', () => {
      if (!menuController && typeof ensureMenuController === 'function') ensureMenuController();
    }, { once: true, passive: true });
    menuBtn.addEventListener('focus', () => {
      if (!menuController && typeof ensureMenuController === 'function') ensureMenuController();
    }, { once: true });
    menuBtn.addEventListener('click', () => setMenuOpen(!menuOpen));
  }
  if (menuAboutBtn && menuPrimary && menuSubmenu) {
    menuAboutBtn.addEventListener('click', () => {
      menuPrimary.classList.add('hidden');
      menuSubmenu.classList.remove('hidden');
    });
  }
  if (menuBackBtn && menuPrimary && menuSubmenu) {
    menuBackBtn.addEventListener('click', () => {
      menuSubmenu.classList.add('hidden');
      menuPrimary.classList.remove('hidden');
    });
  }
  if (menuDialog) {
    menuDialog.querySelectorAll('a').forEach(a => a.addEventListener('click', () => setMenuOpen(false)));
    window.addEventListener('keydown', e => {
      if (e.key === 'Escape' && menuOpen) setMenuOpen(false);
    });
  }

  // =========================================================================
  // 3. HERO SECTION: SCROLL EXPANSION (--g2-e), WORD FIT & 2-SLIDE CAROUSEL
  // =========================================================================
  const heroSlidesData = (HOME_DATA?.heroSlides && HOME_DATA.heroSlides.length >= 2)
    ? HOME_DATA.heroSlides
    : [
        {
          lines: ['PropNest', 'Aleya'],
          href: '/properties/',
          cardTitle: 'PropNest Aleya',
          cardLoc: 'DHANMONDI',
          cardImg: 'https://www.golpoholdings.com/golpo/golpo-aleya/golpo-aleya-exterior-dusk.m.avif',
          num: '01'
        },
        {
          lines: ['PropNest', 'Dar-E-Salam'],
          href: '/properties/',
          cardTitle: 'PropNest Dar-E-Salam',
          cardLoc: 'JOLSHIRI',
          cardImg: 'https://www.golpoholdings.com/golpo/golpo-dar-e-salam/exterior-hero.m.avif',
          num: '02'
        }
      ];

  let heroSlideIdx = 0;
  let heroPaused = prefersReducedMotion;
  let heroTimer = null;

  if (heroSection) {
    const stickyWrap = heroSection.querySelector('.sticky');
    const track = heroSection.querySelector('.g2-hero-frame > div.flex');
    const slideEls = track ? Array.from(track.children) : [];
    const sheets = Array.from(heroSection.querySelectorAll('.g2-hero-sheet'));

    const leftOverlay = heroSection.querySelector('.z-40[style*="text-shadow"]');
    const statusLine = leftOverlay ? leftOverlay.querySelector('[data-hero-status]') : null;
    const titleSpans = leftOverlay ? leftOverlay.querySelectorAll('p.g2-display span') : [];
    const viewLink = leftOverlay ? leftOverlay.querySelector('a') : null;

    const previewCard = heroSection.querySelector('a[aria-label^="Open "]');
    const previewBg = previewCard ? previewCard.querySelector('.g2-bg') : null;
    const previewTitle = previewCard ? previewCard.querySelector('p.g2-display') : null;
    const previewLoc = previewCard ? previewCard.querySelector('p.mt-1') : null;

    const pauseBtn = heroSection.querySelector('button[aria-label*="Pause"], button[aria-label*="Play"]');
    const prevBtn = heroSection.querySelector('button[aria-label="Previous project"]');
    const nextBtn = heroSection.querySelector('button[aria-label="Next project"]');
    const dotBtns = Array.from(heroSection.querySelectorAll('button[aria-label^="Go to "]'));
    const dwellBar = heroSection.querySelector('.g2-dwell');
    const counterSpan = heroSection.querySelector('span.tabular-nums');

    let heroMaxScroll = 1;
    let heroInView = true;

    function fitHeroWords() {
      const w = heroSection.clientWidth || window.innerWidth;
      heroMaxScroll = Math.max(1, heroSection.offsetHeight - window.innerHeight);
      heroSection.style.setProperty('--g2-hero-w', `${w}px`);
      sheets.forEach(sheet => {
        const wordP = sheet.querySelector('p.g2-display.text-transparent');
        if (wordP && sheet.clientWidth > 0) {
          const naturalW = wordP.scrollWidth;
          const fit = naturalW > sheet.clientWidth ? sheet.clientWidth / naturalW : 1;
          sheet.style.setProperty('--g2-word-fit', fit.toFixed(4));
        }
      });
    }

    function renderHeroSlide(idx) {
      heroSlideIdx = (idx + heroSlidesData.length) % heroSlidesData.length;
      const d = heroSlidesData[heroSlideIdx];

      if (track) track.style.transform = `translateX(calc(${-heroSlideIdx * 50}% + 0px))`;

      slideEls.forEach((el, i) => {
        const active = i === heroSlideIdx;
        el.setAttribute('aria-hidden', active ? 'false' : 'true');
        el.classList.toggle('max-md:z-[2]', active);
        el.classList.toggle('max-md:scale-100', active);
        el.classList.toggle('max-md:opacity-100', active);
        el.classList.toggle('max-md:z-[1]', !active);
        el.classList.toggle('max-md:scale-[1.06]', !active);
        el.classList.toggle('max-md:opacity-0', !active);
      });

      if (statusLine && d.statusLabel) {
        statusLine.textContent = d.statusLabel;
      }
      if (titleSpans.length >= 2) {
        titleSpans[0].textContent = d.lines[0];
        titleSpans[1].textContent = d.lines[1];
      }
      if (viewLink) viewLink.setAttribute('href', d.href);

      if (previewCard) {
        previewCard.setAttribute('aria-label', `Open ${d.cardTitle}`);
        previewCard.setAttribute('href', d.href);
      }
      if (previewBg) {
        previewBg.style.setProperty('--g2-src-sm', `url(${d.cardImg})`);
        previewBg.style.setProperty('--g2-src-lg', `url(${d.cardImg})`);
      }
      if (previewTitle) previewTitle.textContent = d.cardTitle;
      if (previewLoc) previewLoc.textContent = d.cardLoc;

      dotBtns.forEach((btn, i) => {
        const active = i === heroSlideIdx;
        btn.setAttribute('aria-pressed', active ? 'true' : 'false');
        btn.style.width = active ? '40px' : '18px';
        btn.style.background = active
          ? 'var(--g2-gold)'
          : 'color-mix(in srgb, var(--g2-sand) 40%, transparent)';
      });

      if (counterSpan) counterSpan.textContent = `${d.num} / 02`;

      if (dwellBar) {
        dwellBar.style.animation = 'none';
        void dwellBar.offsetWidth;
        dwellBar.style.animation = '';
        dwellBar.style.animationDuration = '5200ms';
        dwellBar.style.animationPlayState = (!heroPaused && heroInView && document.visibilityState === 'visible') ? 'running' : 'paused';
      }

      scheduleHeroNext();
    }

    function scheduleHeroNext() {
      if (heroTimer) {
        clearTimeout(heroTimer);
        heroTimer = null;
      }
      const canRun = !heroPaused && heroInView && document.visibilityState === 'visible';
      if (dwellBar) dwellBar.style.animationPlayState = canRun ? 'running' : 'paused';
      if (canRun) {
        heroTimer = setTimeout(() => renderHeroSlide(heroSlideIdx + 1), 5200);
      }
    }

    if ('IntersectionObserver' in window) {
      new IntersectionObserver(
        ([entry]) => {
          heroInView = entry.isIntersecting;
          scheduleHeroNext();
        },
        { rootMargin: '60px 0px' }
      ).observe(heroSection);
    }
    document.addEventListener('visibilitychange', scheduleHeroNext);

    if (prevBtn) prevBtn.addEventListener('click', () => renderHeroSlide(heroSlideIdx - 1));
    if (nextBtn) nextBtn.addEventListener('click', () => renderHeroSlide(heroSlideIdx + 1));
    dotBtns.forEach((btn, i) => btn.addEventListener('click', () => renderHeroSlide(i)));
    if (pauseBtn) {
      pauseBtn.addEventListener('click', () => {
        heroPaused = !heroPaused;
        pauseBtn.setAttribute('aria-pressed', heroPaused ? 'true' : 'false');
        scheduleHeroNext();
      });
    }

    fitHeroWords();
    scheduleHeroNext();
    window.addEventListener('resize', fitHeroWords, { passive: true });
    if (document.fonts && document.fonts.ready) {
      document.fonts.ready.then(fitHeroWords);
    }

    window.__updateHeroScroll = function (scrollY) {
      if (!stickyWrap) return;
      const e = clamp01(scrollY / heroMaxScroll);
      stickyWrap.style.setProperty('--g2-e', e.toFixed(4));
      stickyWrap.style.setProperty('--g2-hero-y', `${(-16 * e).toFixed(2)}px`);
    };
  }

  // =========================================================================
  // 4. GIANT DISPLAY HEADINGS: CONTAINER FIT & 3D LETTER FLIP
  // =========================================================================
  const displayHeadings = Array.from(document.querySelectorAll('div[style*="container-type:inline-size"] > h2.g2-display'));
  const displayHeadingStates = displayHeadings.map(h2 => {
    const spans = Array.from(h2.children).filter(el => !el.classList.contains('sr-only'));
    const measureWrap = spans[0] ? spans[0].firstElementChild : null;
    const visibleWrap = spans[1] || null;
    const letters = visibleWrap ? Array.from(visibleWrap.querySelectorAll('span[style*="perspective"] > span')) : [];
    return { h2, measureWrap, visibleWrap, letters, lastP: -1 };
  });

  function fitDisplayHeadings() {
    displayHeadingStates.forEach(({ h2, measureWrap, visibleWrap }) => {
      const container = h2.parentElement;
      if (!container || !visibleWrap) return;
      const cw = container.clientWidth;
      if (cw <= 0) return;

      const targetEl = measureWrap || visibleWrap;
      const prevFs = targetEl.style.fontSize;
      targetEl.style.fontSize = '100px';
      const w100 = targetEl.scrollWidth || targetEl.getBoundingClientRect().width;
      targetEl.style.fontSize = prevFs;

      if (w100 > 0) {
        const fitted = (cw / w100) * 100;
        if (measureWrap) measureWrap.style.fontSize = `${fitted.toFixed(3)}px`;
        visibleWrap.style.fontSize = `${fitted.toFixed(2)}px`;
      }
    });
  }

  fitDisplayHeadings();
  window.addEventListener('resize', fitDisplayHeadings, { passive: true });
  if (document.fonts && document.fonts.ready) {
    document.fonts.ready.then(() => {
      fitDisplayHeadings();
      if (towerController) towerController.invalidateTitle();
    });
  }

  // =========================================================================
  // 5. PORTFOLIO RAIL (#portfolio): INFINITE AUTO-SCROLL, DRAG & BUTTONS
  // =========================================================================
  if (portfolioSection) {
    const railTrack = portfolioSection.querySelector('.flex.w-max.gap-6');
    const railContainer = railTrack ? railTrack.parentElement : null;
    const pauseRailBtn = portfolioSection.querySelector('button[aria-label="Pause the portfolio rail"]');
    const prevRailBtn = portfolioSection.querySelector('button[aria-label="Previous projects"]');
    const nextRailBtn = portfolioSection.querySelector('button[aria-label="Next projects"]');

    let railX = -320;
    let railTargetOffset = 0;
    let railPaused = prefersReducedMotion;
    let isDragging = false;
    let dragStartX = 0;
    let dragInitialX = 0;
    let railHalfWidth = railTrack ? railTrack.scrollWidth / 2 : 0;
    let railInView = false;
    let railRafId = 0;

    if (railTrack) {
      if ('ResizeObserver' in window) {
        new ResizeObserver(() => {
          railHalfWidth = railTrack.scrollWidth / 2;
        }).observe(railTrack);
      }

      const canRailTick = () =>
        railInView &&
        document.visibilityState === 'visible' &&
        (!railPaused || isDragging || Math.abs(railTargetOffset) > 0.5);

      const stepRail = () => {
        railRafId = 0;
        if (!canRailTick()) return;
        if (!railPaused && !isDragging) railX -= 0.55;
        if (Math.abs(railTargetOffset) > 0.5) {
          const delta = railTargetOffset * 0.12;
          railX += delta;
          railTargetOffset -= delta;
        }
        if (railHalfWidth > 0) {
          if (railX <= -railHalfWidth) railX += railHalfWidth;
          if (railX > 0) railX -= railHalfWidth;
        }
        railTrack.style.transform = `translate3d(${railX.toFixed(1)}px, 0, 0)`;
        railRafId = requestAnimationFrame(stepRail);
      };

      const ensureRailTick = () => {
        if (!railRafId && canRailTick()) {
          railRafId = requestAnimationFrame(stepRail);
        } else if (railRafId && !canRailTick()) {
          cancelAnimationFrame(railRafId);
          railRafId = 0;
        }
      };

      if ('IntersectionObserver' in window) {
        new IntersectionObserver(
          ([entry]) => {
            railInView = entry.isIntersecting;
            ensureRailTick();
          },
          { rootMargin: '120px 0px' }
        ).observe(portfolioSection);
      } else {
        railInView = true;
        ensureRailTick();
      }
      document.addEventListener('visibilitychange', ensureRailTick);

      // Apply initial resting transform cleanly without spinning while offscreen
      railTrack.style.transform = `translate3d(${railX}px, 0, 0)`;

      if (pauseRailBtn) {
        pauseRailBtn.addEventListener('click', () => {
          railPaused = !railPaused;
          pauseRailBtn.setAttribute('aria-pressed', railPaused ? 'true' : 'false');
          ensureRailTick();
        });
      }
      if (prevRailBtn) {
        prevRailBtn.addEventListener('click', () => {
          const card = railTrack.querySelector('a');
          railTargetOffset += card ? card.clientWidth + 24 : 360;
          ensureRailTick();
        });
      }
      if (nextRailBtn) {
        nextRailBtn.addEventListener('click', () => {
          const card = railTrack.querySelector('a');
          railTargetOffset -= card ? card.clientWidth + 24 : 360;
          ensureRailTick();
        });
      }
      if (railContainer) {
        railContainer.addEventListener('pointerdown', e => {
          isDragging = true;
          dragStartX = e.clientX;
          dragInitialX = railX;
          ensureRailTick();
        });
        window.addEventListener('pointermove', e => {
          if (isDragging) railX = dragInitialX + (e.clientX - dragStartX);
        }, { passive: true });
        window.addEventListener('pointerup', () => {
          if (isDragging) {
            isDragging = false;
            ensureRailTick();
          }
        });
      }
    }
  }

  // =========================================================================
  // 6. LOCATIONS SECTION (#locations): EXACT MERCATOR MAP PROJECTION & PINS
  // =========================================================================
  if (locationsSection) {
    const mapBox = locationsSection.querySelector('.isolate.overflow-hidden');
    let iframe = mapBox ? mapBox.querySelector('iframe') : null;
    const pins = mapBox ? Array.from(mapBox.querySelectorAll('.g2-pin')) : [];

    let pinData = [
      { key: 'aleya', lat: 23.7388125, lng: 90.3780625 },
      { key: 'dar-e-salam', lat: 23.8165375, lng: 90.498703125 },
      { key: 'basundhara', lat: 23.8076875, lng: 90.4576875 },
      { key: 'isho-tower', lat: 23.7719375, lng: 90.4036875 }
    ];
    if (HOME_DATA?.mapPins && HOME_DATA.mapPins.length) {
      pinData = HOME_DATA.mapPins;
    }

    function latLngToWorld(lat, lng) {
      const siny = Math.min(Math.max(Math.sin((lat * Math.PI) / 180), -0.9999), 0.9999);
      return {
        x: 256 * (0.5 + lng / 360),
        y: 256 * (0.5 - Math.log((1 + siny) / (1 - siny)) / (4 * Math.PI))
      };
    }

    let currentEmbedKey = '';

    function layoutLocationsMap() {
      if (!mapBox) return;
      const w = mapBox.clientWidth;
      const h = mapBox.clientHeight;
      if (w <= 0 || h <= 0) return;

      const isMobile = window.innerWidth < 768;
      // On Desktop/Tablet (>=768px), shift center west (23.777681, 90.389288) at z=13 so all 4 pins sit right of the project list;
      // on Mobile (<768px), use exact (23.787162, 90.438383) at z=11 with scale(1) so all 4 pins fit cleanly above the list.
      const centerLat = isMobile ? 23.787162 : 23.777681;
      const centerLng = isMobile ? 90.438383 : 90.389288;
      const zoom = isMobile ? 11 : 13;
      const cssScale = isMobile ? 1 : Math.min(1, w / 1430);
      const pxScale = Math.pow(2, zoom) * cssScale;

      const embedKey = `${centerLat},${centerLng},${zoom}`;
      if (iframe) {
        if (currentEmbedKey !== embedKey) {
          currentEmbedKey = embedKey;
          const nextSrc = `https://maps.google.com/maps?ll=${centerLat},${centerLng}&z=${zoom}&t=m&hl=en&output=embed`;
          if (iframe.getAttribute('src') !== nextSrc) {
            const freshIframe = iframe.cloneNode(false);
            freshIframe.removeAttribute('loading');
            freshIframe.setAttribute('src', nextSrc);
            iframe.replaceWith(freshIframe);
            iframe = freshIframe;
          }
        }
        iframe.style.width = `${Math.round(w / cssScale)}px`;
        iframe.style.height = `${Math.round(h / cssScale)}px`;
        iframe.style.transform = `scale(${cssScale === 1 ? '1' : cssScale.toFixed(6)})`;
        iframe.style.transformOrigin = '0px 0px';
      }

      const cWorld = latLngToWorld(centerLat, centerLng);
      pins.forEach((pin, idx) => {
        const p = pinData[idx];
        if (!p) return;
        const pWorld = latLngToWorld(p.lat, p.lng);
        const x = w / 2 + (pWorld.x - cWorld.x) * pxScale;
        const y = h / 2 + (pWorld.y - cWorld.y) * pxScale;
        pin.style.left = `${(x - 14).toFixed(2)}px`;
        pin.style.top = `${(y - 38).toFixed(2)}px`;
      });
    }

    layoutLocationsMap();
    window.addEventListener('resize', layoutLocationsMap, { passive: true });

    const projectLinks = Array.from(locationsSection.querySelectorAll('ul a'));
    function activatePin(targetKey, href) {
      pins.forEach((pin, idx) => {
        const p = pinData[idx];
        const match = Boolean(
          p && (
            (targetKey && p.key === targetKey) ||
            (href && (href === p.href || href.includes(p.key)))
          )
        );
        pin.classList.toggle('is-active', match);
      });
    }

    projectLinks.forEach(link => {
      const k = link.dataset.pinKey || '';
      const h = link.getAttribute('href') || '';
      link.addEventListener('mouseenter', () => activatePin(k, h));
      link.addEventListener('focus', () => activatePin(k, h));
      link.addEventListener('mouseleave', () => activatePin(null, null));
      link.addEventListener('blur', () => activatePin(null, null));
    });

    pins.forEach(pin => {
      pin.addEventListener('mouseenter', () => pin.classList.add('is-active'));
      pin.addEventListener('mouseleave', () => pin.classList.remove('is-active'));
      pin.addEventListener('click', () => {
        if (pin.dataset.href) window.location.href = pin.dataset.href;
      });
    });
  }

  // =========================================================================
  // 7. SHARED WEBGL RING SHADER (83249) + NOISE TEXTURE + ALPHA BLOOM
  // =========================================================================
  const RING_VERTEX_SHADER = `
  varying vec2 vUv;
  void main() {
    vUv = uv;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }
`;

  const RING_FRAGMENT_SHADER = `
  #define SPEED_OUTER 10.0
  #define SPEED_INNER 40.0
  #define SCALE_RING_COUNT 3.0
  #define SCALE_RING_LENGTH 1.2

  uniform float uTime;
  uniform float uProgress;
  uniform sampler2D uNoiseTexture;
  uniform vec3  uInnerColor;
  uniform vec3  uOuterColor;
  uniform float uAlpha;
  uniform float uLightMode;
  // 1 = a whole ring, brightest at one point (the menu); 0 = the comet (the home tower)
  uniform float uFull;
  uniform float uBoost;

  varying vec2 vUv;

  vec3 blendAdd(vec3 base, vec3 blend) { return min(base + blend, vec3(1.0)); }

  void main() {
    vec4 color = vec4(0.0);
    color.a = 1.0;

    float iterations = 3.0;
    for (float i = 0.0; i < 3.0; i++) {
      float progress = i / (iterations - 1.0);

      float bandDist  = abs(vUv.y - progress);
      float intensity = 1.0 - smoothstep(0.0, 0.25, bandDist);

      vec2 uv = vUv;
      uv.y *= SCALE_RING_COUNT;
      uv.x /= SCALE_RING_LENGTH;
      uv.x -= uTime / ((i * (SPEED_INNER - SPEED_OUTER)) + SPEED_OUTER);

      vec3 ringColor = mix(uInnerColor, uOuterColor, progress);
      float n = smoothstep(0.2, 0.8, texture2D(uNoiseTexture, uv).r);
      ringColor = mix(vec3(0.0), ringColor.rgb, n * intensity);

      color.rgb = blendAdd(color.rgb, ringColor);
    }

    // soften both radial rims so the cone has no cut edge
    color.rgb *= smoothstep(0.0, 0.15, vUv.y) * smoothstep(1.0, 0.85, vUv.y) * 2.0;

    float progress = clamp(uProgress * 0.5 + 0.5, 0.0, 1.0);
    float tailLength = 0.5;
    float headFade = 0.15;
    float tailStart = progress - tailLength;
    float peakPos = progress - headFade;

    float cometMask = 0.0;
    if (vUv.x > tailStart && vUv.x <= peakPos) {
      cometMask = smoothstep(tailStart, peakPos, vUv.x);
    } else if (vUv.x > peakPos && vUv.x <= progress) {
      cometMask = 1.0 - smoothstep(peakPos, progress, vUv.x);
    }

    float around = 0.5 + 0.5 * cos((vUv.x - 0.5) * 6.2831853);
    cometMask = mix(cometMask, 0.45 + 0.55 * around * around, uFull);

    color.rgb *= 1.5 * uBoost;

    float lum = 0.2126 * color.r + 0.7152 * color.g + 0.0722 * color.b;
    float maxColor = max(color.r, max(color.g, color.b));
    float alphaBase = mix(lum, smoothstep(0.0, 0.8, maxColor) * 1.5, uLightMode);
    alphaBase = mix(alphaBase, smoothstep(0.0, 0.4, maxColor) * 1.8, uFull);
    color.rgb *= 1.0 + 0.6 * uFull;

    gl_FragColor = color;
    gl_FragColor.a = clamp(alphaBase * cometMask * uAlpha, 0.0, 1.0);
  }
`;

  function createRingNoiseTexture(size = 128) {
    const c = document.createElement('canvas');
    c.width = c.height = size;
    const ctx = c.getContext('2d');
    const img = ctx.createImageData(size, size);
    const data = img.data;
    let seed = 42;
    const rand = () => ((seed = (16807 * seed) % 0x7fffffff) - 1) / 0x7ffffffe;
    for (let y = 0; y < size; y++) {
      for (let x = 0; x < size; x++) {
        const idx = (y * size + x) * 4;
        const val = Math.floor(
          255 *
            Math.min(
              1,
              0.5 * (0.5 * Math.sin(0.06 * x + 0.02 * y) + 0.5) +
                0.3 * (0.3 * Math.sin(0.12 * x - 0.08 * y) + 0.5) +
                0.15 * (0.2 * Math.cos(0.03 * x + 0.15 * y) + 0.5) +
                0.075 * rand()
            )
        );
        data[idx] = data[idx + 1] = data[idx + 2] = val;
        data[idx + 3] = 255;
      }
    }
    ctx.putImageData(img, 0, 0);
    const tex = new THREE.CanvasTexture(c);
    tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
    return tex;
  }

  function createCometRingMaterial({ noiseTex, isLight = false, full = 0, alpha = 0, boost = 1 }) {
    return new THREE.ShaderMaterial({
      side: THREE.DoubleSide,
      transparent: true,
      depthWrite: false,
      blending: isLight ? THREE.NormalBlending : THREE.AdditiveBlending,
      uniforms: {
        uTime: { value: 0 },
        uNoiseTexture: { value: noiseTex },
        uInnerColor: { value: new THREE.Color(isLight ? 0xe65c00 : 0xff9966) },
        uOuterColor: { value: new THREE.Color(isLight ? 0x992600 : 0xff4d0d) },
        uProgress: { value: 1 },
        uAlpha: { value: alpha },
        uLightMode: { value: +isLight },
        uFull: { value: full },
        uBoost: { value: boost }
      },
      vertexShader: RING_VERTEX_SHADER,
      fragmentShader: RING_FRAGMENT_SHADER
    });
  }

  function createAlphaBloomPass(strength, radius, threshold) {
    const pass = new UnrealBloomPass(new THREE.Vector2(1, 1), strength, radius, threshold);
    pass.blendMaterial.blending = THREE.CustomBlending;
    pass.blendMaterial.blendEquation = THREE.AddEquation;
    pass.blendMaterial.blendSrc = THREE.OneFactor;
    pass.blendMaterial.blendDst = THREE.OneFactor;
    pass.blendMaterial.blendEquationAlpha = THREE.AddEquation;
    pass.blendMaterial.blendSrcAlpha = THREE.ZeroFactor;
    pass.blendMaterial.blendDstAlpha = THREE.OneFactor;
    return pass;
  }

  // =========================================================================
  // 8. SECTION 8: 3D ARCHITECTURAL TOWER (GOLPO ALEYA GLB + HDR + BLOOM + RING)
  // =========================================================================
  function measureBuilding(root) {
    root.updateMatrixWorld(true);
    const meshes = [];
    let totalVerts = 0;
    root.traverse(obj => {
      if (obj.isMesh && obj.geometry?.attributes?.position) {
        meshes.push(obj);
        totalVerts += obj.geometry.attributes.position.count;
      }
    });
    const box = new THREE.Box3().setFromObject(root);
    const fallback = {
      centre: box.getCenter(new THREE.Vector3()),
      footprint: Math.max(box.max.x - box.min.x, box.max.z - box.min.z) || 1,
      floor: box.min.y,
      height: box.max.y - box.min.y || 1,
      withPlot: false
    };
    if (!meshes.length) return fallback;

    const step = Math.max(1, Math.floor(totalVerts / 20000));
    const pts = [];
    const v = new THREE.Vector3();
    let minY = Infinity;
    let maxY = -Infinity;
    for (const m of meshes) {
      const pos = m.geometry.attributes.position;
      for (let i = 0; i < pos.count; i += step) {
        v.fromBufferAttribute(pos, i).applyMatrix4(m.matrixWorld);
        pts.push(v.x, v.y, v.z);
        if (v.y < minY) minY = v.y;
        if (v.y > maxY) maxY = v.y;
      }
    }
    const spanY = maxY - minY;
    if (!(spanY > 0)) return fallback;

    const splitY = minY + spanY / 3;
    const cell = Math.max(fallback.footprint / 200, spanY / 400, 1e-6);
    const key = (cx, cz) => (cx + 1048576) * 2097152 + (cz + 1048576);
    const occ = new Set();
    let peakX = 0;
    let peakZ = 0;
    let peakY = -Infinity;

    for (const m of meshes) {
      const pos = m.geometry.attributes.position;
      const idxAttr = m.geometry.index?.array;
      const me = m.matrixWorld.elements;
      const count = pos.count;
      const wx = new Float32Array(count);
      const wy = new Float32Array(count);
      const wz = new Float32Array(count);
      for (let i = 0; i < count; i++) {
        const px = pos.getX(i);
        const py = pos.getY(i);
        const pz = pos.getZ(i);
        wx[i] = me[0] * px + me[4] * py + me[8] * pz + me[12];
        wy[i] = me[1] * px + me[5] * py + me[9] * pz + me[13];
        wz[i] = me[2] * px + me[6] * py + me[10] * pz + me[14];
      }
      const triLen = idxAttr ? idxAttr.length : count;
      for (let i = 0; i + 2 < triLen; i += 3) {
        const i0 = idxAttr ? idxAttr[i] : i;
        const i1 = idxAttr ? idxAttr[i + 1] : i + 1;
        const i2 = idxAttr ? idxAttr[i + 2] : i + 2;
        const triMaxY = Math.max(wy[i0], wy[i1], wy[i2]);
        if (triMaxY <= splitY) continue;
        if (triMaxY > peakY) {
          peakY = triMaxY;
          const pk = wy[i0] === triMaxY ? i0 : wy[i1] === triMaxY ? i1 : i2;
          peakX = wx[pk];
          peakZ = wz[pk];
        }
        const x0 = Math.floor(Math.min(wx[i0], wx[i1], wx[i2]) / cell);
        const x1 = Math.floor(Math.max(wx[i0], wx[i1], wx[i2]) / cell);
        const z0 = Math.floor(Math.min(wz[i0], wz[i1], wz[i2]) / cell);
        const z1 = Math.floor(Math.max(wz[i0], wz[i1], wz[i2]) / cell);
        if (x0 === x1 && z0 === z1) {
          occ.add(key(x0, z0));
        } else if ((x1 - x0 + 1) * (z1 - z0 + 1) <= 4000) {
          for (let x = x0; x <= x1; x++) {
            for (let z = z0; z <= z1; z++) occ.add(key(x, z));
          }
        }
      }
    }
    if (peakY === -Infinity) return fallback;

    const seedX = Math.floor(peakX / cell);
    const seedZ = Math.floor(peakZ / cell);
    const visited = new Set([key(seedX, seedZ)]);
    const stack = [seedX, seedZ];
    while (stack.length) {
      const cz = stack.pop();
      const cx = stack.pop();
      for (let dx = -2; dx <= 2; dx++) {
        for (let dz = -2; dz <= 2; dz++) {
          const nk = key(cx + dx, cz + dz);
          if (!visited.has(nk) && occ.has(nk)) {
            visited.add(nk);
            stack.push(cx + dx, cz + dz);
          }
        }
      }
    }
    const coreBox = new THREE.Box3();
    for (let i = 0; i < pts.length; i += 3) {
      if (pts[i + 1] > splitY && visited.has(key(Math.floor(pts[i] / cell), Math.floor(pts[i + 2] / cell)))) {
        coreBox.expandByPoint(v.set(pts[i], pts[i + 1], pts[i + 2]));
      }
    }
    if (coreBox.isEmpty()) return fallback;

    const footprint = Math.max(coreBox.max.x - coreBox.min.x, coreBox.max.z - coreBox.min.z) || fallback.footprint;
    const withPlot = fallback.footprint > 2 * footprint;
    let floorY = minY;
    if (withPlot) {
      const bandY = spanY / 10;
      const binH = Math.max(spanY / 500, 1e-6);
      const areaBins = new Map();
      const triStep = Math.max(1, Math.floor((totalVerts / 3) / 20000));
      const a = new THREE.Vector3();
      const b = new THREE.Vector3();
      const c = new THREE.Vector3();
      const nrm = new THREE.Vector3();
      for (const m of meshes) {
        const pos = m.geometry.attributes.position;
        const idxAttr = m.geometry.index;
        const tris = idxAttr ? idxAttr.count / 3 : pos.count / 3;
        for (let t = 0; t < tris; t += triStep) {
          const i0 = idxAttr ? idxAttr.getX(3 * t) : 3 * t;
          const i1 = idxAttr ? idxAttr.getX(3 * t + 1) : 3 * t + 1;
          const i2 = idxAttr ? idxAttr.getX(3 * t + 2) : 3 * t + 2;
          a.fromBufferAttribute(pos, i0).applyMatrix4(m.matrixWorld);
          b.fromBufferAttribute(pos, i1).applyMatrix4(m.matrixWorld);
          c.fromBufferAttribute(pos, i2).applyMatrix4(m.matrixWorld);
          const avgY = (a.y + b.y + c.y) / 3;
          if (avgY > minY + bandY) continue;
          c.sub(a);
          nrm.subVectors(b, a).cross(c);
          const len = nrm.length();
          if (!len || Math.abs(nrm.y) / len < 0.9) continue;
          const bin = Math.round(avgY / binH);
          areaBins.set(bin, (areaBins.get(bin) ?? 0) + len / 2);
        }
      }
      let bestArea = 0;
      for (const [bin, area] of areaBins) {
        if (area > bestArea) {
          bestArea = area;
          floorY = bin * binH;
        }
      }
    }
    return {
      centre: new THREE.Vector3((coreBox.min.x + coreBox.max.x) / 2, floorY, (coreBox.min.z + coreBox.max.z) / 2),
      footprint,
      floor: floorY,
      height: maxY - floorY,
      withPlot
    };
  }

  function fitBuilding(root) {
    const saved = root.userData?.golpoFit;
    if (saved && Array.isArray(saved.centre) && saved.footprint > 0 && saved.height > 0) {
      return {
        centre: new THREE.Vector3(...saved.centre),
        footprint: saved.footprint,
        floor: saved.floor,
        height: saved.height,
        withPlot: Boolean(saved.withPlot)
      };
    }
    return measureBuilding(root);
  }

  function initTowerThreeJS(section, backdropContainer, canvas, titleDiv, titleSpan) {
    let theme = g2.getAttribute('data-g2-theme') || 'dark';
    const isLight = () => theme === 'light';

    const updateBackdropGradient = () => {
      if (isLight()) {
        section.style.removeProperty('--g2-tower-halo');
        section.style.background = '';
      } else {
        section.style.setProperty('--g2-tower-halo', '0.45');
        section.style.background = 'linear-gradient(to bottom, var(--g2-ink) 0, var(--g2-tower-ground, #071b30) 30vh, var(--g2-tower-ground, #071b30) calc(100% - 30vh), var(--g2-ink) 100%)';
      }
      backdropContainer.style.maskImage = 'linear-gradient(to bottom, #000 0%, #000 82%, transparent 100%)';
      backdropContainer.style.webkitMaskImage = backdropContainer.style.maskImage;
      backdropContainer.style.background = isLight()
        ? 'radial-gradient(24% 30% at 50% 78%, rgba(255,170,90,0.32), transparent 72%), radial-gradient(34% 60%, rgba(80,150,255,0.16), transparent 75%)'
        : 'radial-gradient(ellipse 24% 30% at 50% 78%, rgba(255,150,60,0.45), transparent 72%), radial-gradient(ellipse 34% 60% at 50% 50%, rgba(60,150,255,calc(0.45 * var(--g2-tower-halo, 1))), transparent 75%), radial-gradient(ellipse 70% 90% at 50% 50%, rgba(34,96,150,calc(0.6 * var(--g2-tower-halo, 1))), transparent 75%)';
    };
    updateBackdropGradient();

    const renderer = new THREE.WebGLRenderer({
      canvas,
      antialias: true,
      alpha: true,
      powerPreference: 'high-performance',
      stencil: false
    });
    renderer.setClearColor(0, 0);
    renderer.debug.checkShaderErrors = false;
    const baseDpr = Math.min(window.devicePixelRatio || 1, 1.5);
    let renderScale = 1.0;
    let useComposer = !prefersReducedMotion;
    renderer.setPixelRatio(Math.min(baseDpr, 1.25));
    renderer.toneMapping = THREE.NeutralToneMapping;
    renderer.toneMappingExposure = 1;

    const scene = new THREE.Scene();
    let baseFogDensity = isLight() ? 0.0006 : 0.0012;
    const fogColor = new THREE.Color(isLight() ? 0xf3ece3 : 0x0d3a5e);
    const fog = new THREE.FogExp2(fogColor.getHex(), baseFogDensity);
    scene.fog = fog;

    const camera = new THREE.PerspectiveCamera(40, 1, 0.1, 2000);
    camera.position.set(0, 45, 230);

    const composerTarget = new THREE.WebGLRenderTarget(1, 1, {
      type: THREE.HalfFloatType,
      samples: 0
    });
    const composer = new EffectComposer(renderer, composerTarget);
    composer.addPass(new RenderPass(scene, camera));

    const bloomPass = createAlphaBloomPass(
      isLight() ? 0.2 : 0.45,
      isLight() ? 0.2 : 0.5,
      0.92
    );
    composer.addPass(bloomPass);

    const outputPass = new OutputPass();
    composer.addPass(outputPass);

    const gradeShader = {
      uniforms: {
        tDiffuse: { value: null },
        uTime: { value: 0 },
        uGrain: { value: 0.03 }
      },
      vertexShader: `
        varying vec2 vUv;
        void main() {
          vUv = uv;
          gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
        }`,
      fragmentShader: `
        uniform sampler2D tDiffuse;
        uniform float uTime;
        uniform float uGrain;
        varying vec2 vUv;
        float grainHash(vec2 p) { return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453); }
        void main() {
          vec4 c = texture2D(tDiffuse, vUv);
          vec3 col = c.rgb;
          float l = dot(col, vec3(0.299, 0.587, 0.114));
          col += vec3(-0.012, 0.004, 0.022) * (1.0 - l) + vec3(0.025, 0.01, -0.018) * l;
          col = mix(vec3(l), col, 1.1);
          col = (col - 0.5) * 1.06 + 0.5;
          col *= mix(0.86, 1.0, smoothstep(0.95, 0.35, length(vUv - 0.5)));
          col += (grainHash(floor(gl_FragCoord.xy) + fract(uTime) * 97.0) - 0.5) * uGrain;
          gl_FragColor = vec4(c.rgb + (clamp(col, 0.0, 1.0) - c.rgb) * c.a, c.a);
        }`
    };
    const gradePass = new ShaderPass(gradeShader);
    composer.addPass(gradePass);

    // Consolidated 4-light architectural rig (sky/ground hemi + warm key + cool rim + ember lobby)
    const hemiLight = new THREE.HemisphereLight(0xeef4ff, 0xffd8b0, isLight() ? 1.15 : 1.25);
    scene.add(hemiLight);

    const keyLight = new THREE.DirectionalLight(0xffe2c4, 2.05);
    keyLight.position.set(50, 100, 50);
    scene.add(keyLight);

    const lobbyLight = new THREE.PointLight(0xff6524, 0.95, 150);
    lobbyLight.position.set(0, -20, 20);
    scene.add(lobbyLight);

    const rimLeft = new THREE.DirectionalLight(0x9fc4ff, 1.5);
    rimLeft.position.set(-120, 60, -160);
    scene.add(rimLeft);

    const rootGroup = new THREE.Group();
    rootGroup.position.y = -80;
    scene.add(rootGroup);

    const buildingSpinGroup = new THREE.Group();
    rootGroup.add(buildingSpinGroup);

    const fadeUniforms = {
      base: { value: 0 },
      height: { value: 16 },
      near: { value: 1e6 },
      far: { value: 2e6 }
    };

    let loadedModel = null;
    let assetsStarted = false;
    let warmupFramesLeft = 10;
    let perfAccumMs = 0;
    let perfSamples = 0;
    let perfTier = 0;
    canvas.dataset.pnRenderTier = '0';

    // Ring (single lightweight 128-seg spiral ribbon; direct-mode luminosity handled in shader via uBoost)
    const noiseTex = createRingNoiseTexture(128);
    const ringMat = createCometRingMaterial({
      noiseTex,
      isLight: isLight(),
      full: 0,
      alpha: 0,
      boost: useComposer ? 1 : (isLight() ? 1.15 : 1.32)
    });
    const ringGeo = new THREE.CylinderGeometry(85, 48, 0, 128, 1, true);
    const ringMesh = new THREE.Mesh(ringGeo, ringMat);
    ringMesh.position.set(0, 4.5, 0);
    ringMesh.renderOrder = 1;

    const ringPivot = new THREE.Group();
    ringPivot.position.y = 80;
    ringPivot.add(ringMesh);
    rootGroup.add(ringPivot);

    // Deferred HDR Environment + Meshopt GLB load (avoids competing with initial Hero paint)
    const hdrUrl = PN_CFG.towerHdrUrl || '/static/assets/golpo-aleya-evening-sky.hdr';
    const glbUrl = PN_CFG.towerGlbUrl || '/static/assets/golpo-aleya-building-coloured.glb';

    function bakeEnvironment(skyMat) {
      const pmremGenerator = new THREE.PMREMGenerator(renderer);
      const envScene = new THREE.Scene();
      const skyGeo = new THREE.SphereGeometry(400, 48, 24);
      const skyMesh = new THREE.Mesh(skyGeo, skyMat);
      envScene.add(skyMesh);
      scene.environment = pmremGenerator.fromScene(envScene, 0.02, 0.1, 1000).texture;
      envScene.clear();
      skyGeo.dispose();
      skyMat.dispose();
      pmremGenerator.dispose();
    }

    function startTowerAssetsLoad() {
      if (assetsStarted) return;
      assetsStarted = true;

      const hdrPromise = new HDRLoader()
        .loadAsync(hdrUrl)
        .then(hdr => {
          hdr.wrapS = THREE.RepeatWrapping;
          hdr.repeat.x = -1;
          const skyMat = new THREE.MeshBasicMaterial({
            map: hdr,
            side: THREE.BackSide,
            depthWrite: false,
            toneMapped: false
          });
          scene.environmentIntensity = 0.3;
          scene.environmentRotation.y = Math.PI;
          bakeEnvironment(skyMat);
          hdr.dispose();
        })
        .catch(() => {
          const skyFallback = new THREE.ShaderMaterial({
            side: THREE.BackSide,
            depthWrite: false,
            vertexShader: `
              varying vec3 vDir;
              void main() {
                vDir = normalize(position);
                gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
              }`,
            fragmentShader: `
              varying vec3 vDir;
              void main() {
                float y = vDir.y;
                vec3 horizon = vec3(1.0, 0.6, 0.4) * 1.1;
                vec3 c = y < 0.0
                  ? mix(horizon * 0.35, vec3(0.06, 0.055, 0.055), smoothstep(0.0, 0.25, -y))
                  : mix(mix(horizon, vec3(0.5, 0.64, 0.9), smoothstep(0.0, 0.07, y)), vec3(0.1, 0.2, 0.48), smoothstep(0.1, 0.9, y));
                float sun = max(dot(normalize(vDir.xz + 1e-4), normalize(vec2(-0.6, -0.8))), 0.0);
                c += vec3(1.0, 0.5, 0.25) * pow(sun, 6.0) * smoothstep(0.35, 0.0, abs(y)) * 0.8;
                gl_FragColor = vec4(c, 1.0);
              }`
          });
          bakeEnvironment(skyFallback);
        });

      const nextFrame = () => new Promise(r => requestAnimationFrame(r));

      (async () => {
        try {
          await MeshoptDecoder.ready;
          const [gltf] = await Promise.all([
            new GLTFLoader().setMeshoptDecoder(MeshoptDecoder).loadAsync(glbUrl),
            hdrPromise
          ]);
          await nextFrame();
          const model = gltf.scene;
          const fit = fitBuilding(model);
          const s = Math.min(62 / (1.4 * fit.footprint), 150 / fit.height);
          model.scale.setScalar(s);
          model.position.set(-fit.centre.x * s, -fit.floor * s, -fit.centre.z * s);
          model.userData.withPlot = fit.withPlot;
          model.userData.towerWidth = fit.footprint * s;
          model.userData.topY = fit.height * s;
          model.updateMatrixWorld(true);

          const withPlot = fit.withPlot;
          const plotSafeRadius = 0.75 * fit.footprint * s;
          const matBounds = new Map();
          const cornerVec = new THREE.Vector3();

          // Measure per-material conservative local Y & XZ bounds so upper tower opaque
          // materials retain full hardware Early-Z culling (no transparent / discard).
          model.traverse(obj => {
            if (!obj.isMesh || !obj.geometry) return;
            if (!obj.geometry.boundingBox) obj.geometry.computeBoundingBox();
            const bb = obj.geometry.boundingBox;
            let localMinY = Infinity;
            let localMaxXZ = 0;
            for (let ix = 0; ix < 2; ix++) {
              const cx = ix ? bb.max.x : bb.min.x;
              for (let iy = 0; iy < 2; iy++) {
                const cy = iy ? bb.max.y : bb.min.y;
                for (let iz = 0; iz < 2; iz++) {
                  const cz = iz ? bb.max.z : bb.min.z;
                  cornerVec.set(cx, cy, cz).applyMatrix4(obj.matrixWorld);
                  if (cornerVec.y < localMinY) localMinY = cornerVec.y;
                  const rxz = Math.hypot(cornerVec.x, cornerVec.z);
                  if (rxz > localMaxXZ) localMaxXZ = rxz;
                }
              }
            }
            const mats = Array.isArray(obj.material) ? obj.material : [obj.material];
            for (const mat of mats) {
              if (!mat) continue;
              const prev = matBounds.get(mat);
              if (!prev) {
                matBounds.set(mat, { minY: localMinY, maxXZ: localMaxXZ });
              } else {
                if (localMinY < prev.minY) prev.minY = localMinY;
                if (localMaxXZ > prev.maxXZ) prev.maxXZ = localMaxXZ;
              }
            }
          });

          const fadeExpr = withPlot
            ? 'gl_FragColor.a *= (1.0 - smoothstep(uFadeNear, uFadeFar, length(vGroundXZ))) * smoothstep(uFadeBase + 0.40, uFadeBase + 1.40, vGroundY);'
            : 'gl_FragColor.a *= smoothstep(0.0, 1.0, clamp((vGroundY - uFadeBase) / uFadeH, 0.0, 1.0));';

          const configuredMats = new Set();
          const matRemap = new Map();
          const keepPbrRe = /^(Glass_|Frames_Bronze|Rails_Anthracite|Cladding_Charcoal|Bronze|Bola_Glass|Chandelier_Light)/i;
          model.traverse(obj => {
            if (!obj.isMesh) return;
            if (obj.geometry && obj.geometry.index && obj.geometry.index.count > 150000) {
              const oldIdx = obj.geometry.index;
              const arr = oldIdx.array;
              const triCount = (arr.length / 3) | 0;
              const TypedArr = arr instanceof Uint32Array ? Uint32Array : Uint16Array;
              const kept = new TypedArr(((triCount >> 1) + 6) * 3);
              let w = 0;
              for (let t = 0; t < triCount; t++) {
                if (((t / 6) | 0) % 2 === 0) {
                  const b = t * 3;
                  kept[w++] = arr[b];
                  kept[w++] = arr[b + 1];
                  kept[w++] = arr[b + 2];
                }
              }
              obj.geometry.setIndex(new THREE.BufferAttribute(kept.subarray(0, w), 1));
            }

            const isArr = Array.isArray(obj.material);
            const rawMats = isArr ? obj.material : [obj.material];
            const finalMats = rawMats.map(origMat => {
              if (!origMat) return origMat;
              if (matRemap.has(origMat)) return matRemap.get(origMat);

              let activeMat = origMat;
              if (!keepPbrRe.test(origMat.name || '')) {
                activeMat = new THREE.MeshLambertMaterial({
                  name: origMat.name,
                  color: origMat.color ? origMat.color.clone() : new THREE.Color(0xffffff),
                  map: origMat.map || null,
                  emissive: origMat.emissive ? origMat.emissive.clone() : new THREE.Color(0x000000),
                  emissiveMap: origMat.emissiveMap || null,
                  emissiveIntensity: origMat.emissiveIntensity ?? 1,
                  transparent: !!origMat.transparent,
                  opacity: origMat.opacity ?? 1,
                  alphaTest: origMat.alphaTest || 0,
                  depthWrite: origMat.depthWrite !== false,
                  side: origMat.side,
                  vertexColors: !!origMat.vertexColors
                });
                origMat.dispose();
              }
              matRemap.set(origMat, activeMat);

              if (!configuredMats.has(activeMat)) {
                configuredMats.add(activeMat);
                const mat = activeMat;
                if ('envMapIntensity' in mat) {
                  mat.envMapIntensity = /glass/i.test(mat.name) ? 1.4 : 0.6;
                }
                if (mat.name === 'Glass_Facade') {
                  mat.envMapIntensity = 0.85;
                  mat.roughness = 0.18;
                  mat.metalness = 0.25;
                  if ('clearcoat' in mat) mat.clearcoat = 0;
                  mat.color.setRGB(0.14, 0.32, 0.6);
                  mat.opacity = 0.36;
                } else if (/^(Cladding_Charcoal|Frames_Bronze|Rails_Anthracite)/.test(mat.name)) {
                  mat.color.multiplyScalar(2.6);
                  mat.roughness = Math.max(mat.roughness, 0.55);
                  mat.metalness *= 0.6;
                } else if (/^(Floors_Lit_Interior|Soffit_Timber_Lit|Material__8|Material__2)$/.test(mat.name)) {
                  mat.color.setRGB(0.95, 0.88, 0.76);
                  if (mat.emissive.getHex() !== 0) {
                    mat.emissive.setRGB(1, 0.85, 0.65);
                    mat.emissiveIntensity *= 0.9;
                  }
                } else if (mat.name === 'Glass_Lobby_Lit' || mat.name === 'Chandelier_Light') {
                  mat.emissiveIntensity = 0;
                }

                const alreadyTransparent = mat.transparent || mat.opacity < 1;
                const b = matBounds.get(origMat);
                const skipFadeShader = withPlot && !alreadyTransparent && b && b.minY >= 2.15 && b.maxXZ <= plotSafeRadius;
                if (skipFadeShader) {
                  mat.transparent = false;
                } else {
                  mat.forceSinglePass = !alreadyTransparent;
                  mat.transparent = true;
                  mat.onBeforeCompile = shader => {
                    shader.uniforms.uFadeBase = fadeUniforms.base;
                    shader.uniforms.uFadeH = fadeUniforms.height;
                    shader.uniforms.uFadeNear = fadeUniforms.near;
                    shader.uniforms.uFadeFar = fadeUniforms.far;
                    shader.vertexShader = shader.vertexShader
                      .replace('void main() {', 'varying float vGroundY;\nvarying vec2 vGroundXZ;\nvoid main() {')
                      .replace(
                        '#include <begin_vertex>',
                        '#include <begin_vertex>\n  vec4 gWorld = modelMatrix * vec4(transformed, 1.0);\n  vGroundY = gWorld.y;\n  vGroundXZ = gWorld.xz;'
                      );
                    shader.fragmentShader = shader.fragmentShader
                      .replace(
                        'void main() {',
                        'varying float vGroundY;\nvarying vec2 vGroundXZ;\nuniform float uFadeBase;\nuniform float uFadeH;\nuniform float uFadeNear;\nuniform float uFadeFar;\nvoid main() {'
                      )
                      .replace(
                        '#include <dithering_fragment>',
                        `#include <dithering_fragment>\n  ${fadeExpr}\n  if (gl_FragColor.a < 0.1) discard;`
                      );
                  };
                  if (withPlot) mat.customProgramCacheKey = () => (mat.isMeshLambertMaterial ? 'golpo-plot-l' : 'golpo-plot');
                }
              }
              return activeMat;
            });
            obj.material = isArr ? finalMats : finalMats[0];
          });

          await nextFrame();
          buildingSpinGroup.add(model);
          if (typeof renderer.compileAsync === 'function') {
            await renderer.compileAsync(scene, camera);
          }
          loadedModel = model;
          warmupFramesLeft = 10;
          perfAccumMs = 0;
          perfSamples = 0;
          cachedTitleState = '';
          cachedOffsetKey = '';
          prevFrameMs = 0;
        } catch (err) {
          console.error('Tower 3D load error:', err);
        }
      })();
    }

    if ('IntersectionObserver' in window) {
      const preloadObs = new IntersectionObserver(
        entries => {
          if (entries[0]?.isIntersecting) {
            startTowerAssetsLoad();
            preloadObs.disconnect();
          }
        },
        { rootMargin: '1400px 0px' }
      );
      preloadObs.observe(section);
    }
    const scheduleIdlePreload = () => {
      if ('requestIdleCallback' in window) {
        window.requestIdleCallback(() => startTowerAssetsLoad(), { timeout: 2200 });
      } else {
        setTimeout(startTowerAssetsLoad, 1400);
      }
    };
    if (document.readyState === 'complete') {
      scheduleIdlePreload();
    } else {
      window.addEventListener('load', scheduleIdlePreload, { once: true });
    }

    let ptrX = 0;
    let ptrY = 0;
    window.addEventListener(
      'pointermove',
      e => {
        ptrX = e.clientX / window.innerWidth - 0.5;
        ptrY = e.clientY / window.innerHeight - 0.5;
      },
      { passive: true }
    );

    let framingWidth = 60;
    let ringScale = 1.4;
    let lookLift = 52;
    let isMobileLayout = false;
    let cachedCanvasW = 0;
    let cachedCanvasH = 0;
    let cachedContainerW = 0;
    let cachedContainerH = 0;
    let cachedTitleH = 0;
    let cachedSpanW = 0;
    let lastBackdropOpacity = '';
    let lastProjCamZ = -1;
    let mobileTitleY = -1;
    let desktopOffsetY = 0;
    let cachedOffsetKey = '';
    let cachedTitleState = '';

    function syncRendererSize() {
      const w = cachedCanvasW || canvas.clientWidth;
      const h = cachedCanvasH || canvas.clientHeight;
      if (!w || !h) return;
      const effectiveDpr = Math.max(0.65, Math.min(baseDpr, 1.25) * renderScale);
      renderer.setPixelRatio(effectiveDpr);
      renderer.setSize(w, h, false);
      if (useComposer) {
        composer.setSize(w, h);
        bloomPass.setSize(
          Math.max(64, Math.floor(w * effectiveDpr * 0.55)),
          Math.max(64, Math.floor(h * effectiveDpr * 0.55))
        );
      }
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
    }

    function handleResize() {
      const w = canvas.clientWidth;
      const h = canvas.clientHeight;
      if (!w || !h) return;
      cachedCanvasW = w;
      cachedCanvasH = h;
      cachedContainerW = backdropContainer.clientWidth || w;
      cachedContainerH = backdropContainer.clientHeight || h;
      cachedTitleH = titleDiv ? titleDiv.offsetHeight : 0;
      cachedTitleState = '';
      cachedOffsetKey = '';
      lastProjCamZ = -1;

      syncRendererSize();

      isMobileLayout = window.innerWidth < 768;
      framingWidth = isMobileLayout ? 46 : 60;
      ringScale = isMobileLayout ? 0.82 : 1.4;
      lookLift = isMobileLayout ? 22 : 52;
      buildingSpinGroup.scale.setScalar(isMobileLayout ? 0.72 : 1.35);
    }
    new ResizeObserver(handleResize).observe(canvas);
    handleResize();

    const tmpVec = new THREE.Vector3();
    const tmpCam = new THREE.PerspectiveCamera();

    let elapsedTime = 0;
    let targetProgress = 0;
    let smoothProgress = 0;
    let prevProgress = null;
    let prevFrameMs = 0;
    let ringYaw = 0;

    let inView = false;
    let tabVisible = document.visibilityState === 'visible';
    let rafId = 0;

    function stepAdaptiveGovernor(frameDeltaMs) {
      if (!loadedModel || frameDeltaMs <= 0 || frameDeltaMs > 250) return;
      if (warmupFramesLeft > 0) {
        warmupFramesLeft -= 1;
        return;
      }
      perfAccumMs += frameDeltaMs;
      perfSamples += 1;
      if (perfSamples < 8) return;

      const avgMs = perfAccumMs / perfSamples;
      perfAccumMs = 0;
      perfSamples = 0;

      if (avgMs > 24 && perfTier < 3) {
        if (perfTier === 0 && useComposer) {
          perfTier = 1;
          renderScale = 0.78;
          canvas.dataset.pnRenderTier = '1';
          syncRendererSize();
        } else if (perfTier <= 1 && useComposer) {
          perfTier = 2;
          useComposer = false;
          renderScale = 1.0;
          ringMat.uniforms.uFull.value = 0.08;
          ringMat.uniforms.uBoost.value = isLight() ? 1.15 : 1.32;
          lobbyLight.intensity = 1.25;
          canvas.dataset.pnRenderTier = '2';
          syncRendererSize();
        } else if (perfTier === 2) {
          perfTier = 3;
          renderScale = 0.65;
          canvas.dataset.pnRenderTier = '3';
          syncRendererSize();
        }
      }
    }

    function renderTower() {
      rafId = requestAnimationFrame(renderTower);
      const now = performance.now();
      const rawDeltaMs = prevFrameMs ? (now - prevFrameMs) : 16.67;
      const dt = Math.min(0.1, rawDeltaMs / 1000);
      prevFrameMs = now;
      elapsedTime += dt;

      if (prevProgress !== null) stepAdaptiveGovernor(rawDeltaMs);

      const l = (smoothProgress += (targetProgress - smoothProgress) * (1 - Math.exp(-dt / 0.07)));
      const s = 1 - Math.pow(1 - range01(l, 0, 0.5), 2);
      const c = range01(l, 0, 1);
      const f = easeInOutQuad(range01(l, 0.02, 0.9));
      const u = easeInOutQuad(range01(l, 0, 0.06));
      const m = easeInOutQuad(range01(l, 0.86, 0.98));

      ringMesh.rotation.x = 0.3;
      ringMesh.rotation.z = 0.06;
      if (prevProgress !== null) ringYaw += (c - prevProgress) * Math.PI * 8.5;
      prevProgress = c;
      ringMesh.rotation.y = ringYaw;
      const rScale = isMobileLayout ? ringScale : 0.8 * ringScale;
      ringMesh.scale.setScalar(rScale);

      const topY = (loadedModel?.userData?.topY ?? 105) * buildingSpinGroup.scale.y;
      ringPivot.position.y = THREE.MathUtils.lerp(topY - 18, 4, f);

      const hVal = THREE.MathUtils.lerp(-76, -45, s);
      const cw = cachedContainerW;
      const ch = cachedContainerH;

      // Update DHANMONDI / city backdrop title fit once per layout/font change (zero scroll thrash)
      if (titleDiv && titleSpan && cw && ch) {
        const fontKey = `${cw}x${ch}x${document.fonts.status}`;
        if (fontKey !== cachedTitleState) {
          cachedTitleState = fontKey;
          titleDiv.style.fontSize = '100px';
          const spanW = titleSpan.offsetWidth;
          if (spanW) {
            cachedSpanW = spanW;
            const targetW = cw >= 768 ? 0.86 * cw : cw - 48;
            titleDiv.style.fontSize = `${((100 * targetW) / spanW).toFixed(1)}px`;
            cachedTitleH = titleDiv.offsetHeight;
            mobileTitleY = -1;
            lastProjCamZ = -1;
            if (cw >= 768) titleDiv.style.transform = 'translate3d(0, 84px, 0)';
            titleDiv.style.visibility = cw >= 768 ? 'visible' : 'hidden';
          }
        }
      }

      const tanHalfFov = Math.tan((camera.fov * Math.PI) / 360);
      const ringHalf = 85 * ringScale * 1.1;
      const mobileFitZ = (105 * buildingSpinGroup.scale.y) / 0.62 / (2 * tanHalfFov);
      const targetCamZ = isMobileLayout
        ? Math.max(272, mobileFitZ, framingWidth / (tanHalfFov * camera.aspect))
        : Math.max(272, Math.max(framingWidth, ringHalf) / (tanHalfFov * camera.aspect));
      camera.position.z = targetCamZ;

      if (titleDiv && titleSpan && cw < 768 && loadedModel && ch && (lastProjCamZ !== Math.round(targetCamZ) || mobileTitleY < 0)) {
        lastProjCamZ = Math.round(targetCamZ);
        const origY = rootGroup.position.y;
        rootGroup.position.y = -45;
        rootGroup.updateMatrixWorld(true);
        tmpVec.set(0, loadedModel.userData.topY ?? 0, 0).applyMatrix4(buildingSpinGroup.matrixWorld);
        rootGroup.position.y = origY;
        const mlook = -27 + lookLift;
        tmpCam.copy(camera);
        tmpCam.position.set(0, mlook + 12, targetCamZ);
        tmpCam.lookAt(0, mlook, 0);
        tmpCam.updateMatrixWorld();
        tmpVec.project(tmpCam);
        const apexY = ((1 - tmpVec.y) / 2) * ch;
        const mTop = Math.max(72, apexY - 0.12 * (cachedTitleH || titleSpan.offsetHeight));
        if (Math.abs(mTop - mobileTitleY) >= 0.5) {
          mobileTitleY = mTop;
          titleDiv.style.transform = `translate3d(0, ${mTop.toFixed(1)}px, 0)`;
          titleDiv.style.visibility = 'visible';
        }
      }

      const computedDrop = (() => {
        if (!loadedModel || !titleDiv || !ch || !cachedTitleH) return 0;
        const topRef = cw >= 768 ? 84 : mobileTitleY;
        if (topRef < 0) return 0;
        const key = `${cw}x${ch}x${cachedTitleH}x${Math.round(topRef)}x${Math.round(targetCamZ)}`;
        if (key === cachedOffsetKey) return desktopOffsetY;
        cachedOffsetKey = key;

        const targetLook = -45.6 + lookLift;
        tmpCam.copy(camera);
        tmpCam.position.set(0, targetLook + 12, targetCamZ);
        tmpCam.lookAt(0, targetLook, 0);
        tmpCam.updateMatrixWorld();

        const origY = rootGroup.position.y;
        const projScreenY = py => {
          rootGroup.position.y = py;
          rootGroup.updateMatrixWorld(true);
          tmpVec.set(0, loadedModel.userData.topY ?? 0, 0).applyMatrix4(buildingSpinGroup.matrixWorld).project(tmpCam);
          return ((1 - tmpVec.y) / 2) * ch;
        };
        const y0 = projScreenY(-76);
        const slope = (projScreenY(-86) - y0) / 10;
        rootGroup.position.y = origY;
        rootGroup.updateMatrixWorld(true);
        desktopOffsetY = Math.max(0, (topRef + cachedTitleH + 24 - y0) / slope);
        return desktopOffsetY;
      })();

      rootGroup.position.y = hVal - computedDrop * (1 - easeInOutQuad(range01(l, 0.02, 0.62)));

      fadeUniforms.base.value = rootGroup.position.y;
      fadeUniforms.height.value = 16 * buildingSpinGroup.scale.y;
      const tw = (loadedModel?.userData?.towerWidth ?? 0) * buildingSpinGroup.scale.x;
      fadeUniforms.near.value = tw ? 0.78 * tw : 1e6;
      fadeUniforms.far.value = tw ? 0.98 * tw : 2e6;

      buildingSpinGroup.rotation.y = -0.83 + c * Math.PI * 0.5;
      ringMat.uniforms.uTime.value = 0.5 * elapsedTime;
      const ringAlpha = Math.max(0.55, u) * (1 - m);
      ringMat.uniforms.uAlpha.value = ringAlpha;
      if (useComposer) {
        gradePass.uniforms.uTime.value = elapsedTime;
      }

      const lookY = 0.6 * hVal + lookLift;
      camera.position.x += (26 * ptrX - camera.position.x) * 0.05;
      camera.position.y += (lookY + 12 - 18 * ptrY - camera.position.y) * 0.05;

      fog.density = baseFogDensity * (272 / targetCamZ);
      camera.lookAt(0, lookY, 0);

      if (useComposer) {
        composer.render();
      } else {
        renderer.render(scene, camera);
      }
    }

    function syncActive() {
      const shouldRun = inView && tabVisible;
      if (shouldRun) {
        startTowerAssetsLoad();
        if (!rafId) {
          prevFrameMs = 0;
          renderTower();
        }
      } else if (rafId) {
        cancelAnimationFrame(rafId);
        rafId = 0;
      }
    }

    new IntersectionObserver(
      ([entry]) => {
        inView = entry.isIntersecting;
        syncActive();
      },
      { rootMargin: '80px 0px' }
    ).observe(section);

    document.addEventListener('visibilitychange', () => {
      tabVisible = document.visibilityState === 'visible';
      syncActive();
    });

    return {
      setProgress(p) {
        targetProgress = p;
      },
      setBackdropOpacity(op) {
        const nextStr = op >= 0.999 ? '1' : op <= 0.001 ? '0' : op.toFixed(3);
        if (nextStr !== lastBackdropOpacity) {
          lastBackdropOpacity = nextStr;
          backdropContainer.style.opacity = nextStr;
        }
      },
      invalidateTitle() {
        cachedTitleState = '';
        cachedOffsetKey = '';
      },
      setTheme(nextTheme) {
        theme = nextTheme;
        updateBackdropGradient();
        fogColor.setHex(isLight() ? 0xf3ece3 : 0x0d3a5e);
        fog.color.copy(fogColor);
        baseFogDensity = isLight() ? 0.0006 : 0.0012;
        hemiLight.intensity = isLight() ? 1.15 : 1.25;
        bloomPass.strength = isLight() ? 0.2 : 0.45;
        bloomPass.radius = isLight() ? 0.2 : 0.5;
        ringMat.blending = isLight() ? THREE.NormalBlending : THREE.AdditiveBlending;
        ringMat.uniforms.uLightMode.value = +isLight();
        ringMat.uniforms.uBoost.value = useComposer ? 1 : (isLight() ? 1.15 : 1.32);
        ringMat.uniforms.uInnerColor.value.setHex(isLight() ? 0xe65c00 : 0xff9966);
        ringMat.uniforms.uOuterColor.value.setHex(isLight() ? 0x992600 : 0xff4d0d);
      }
    };
  }

  if (towerSection) {
    const backdropContainer = towerSection.querySelector('.sticky > div.absolute.inset-0');
    const towerTitleDiv = towerSection.querySelector('.g2-display.uppercase');
    const towerTitleSpan = towerTitleDiv ? towerTitleDiv.querySelector('span') : null;
    const towerCanvas = towerSection.querySelector('canvas');
    if (backdropContainer && towerCanvas) {
      towerController = initTowerThreeJS(towerSection, backdropContainer, towerCanvas, towerTitleDiv, towerTitleSpan);
    }
  }

  // =========================================================================
  // 9. MENU DRAWER 3D VISUAL (#g2-menu-canvas): EXACT 3953 + 83249
  // =========================================================================
  function initMenuThreeJS(canvas) {
    const renderer = new THREE.WebGLRenderer({
      canvas,
      antialias: true,
      alpha: true,
      powerPreference: 'high-performance',
      stencil: false
    });
    renderer.setClearColor(0, 0);
    renderer.debug.checkShaderErrors = false;
    const menuDpr = Math.min(window.devicePixelRatio || 1, 1.5);
    renderer.setPixelRatio(Math.min(menuDpr, 1.25));
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(30, 1, 0.1, 100);
    camera.position.set(0, 0.2, 9.6);
    camera.lookAt(0, 0, 0);

    const rootGroup = new THREE.Group();
    rootGroup.rotation.set(-0.1, 0, 0.3);
    scene.add(rootGroup);

    const cylGroup = new THREE.Group();
    rootGroup.add(cylGroup);

    const panelUrls = (Array.isArray(PN_CFG.menuPanels) && PN_CFG.menuPanels.length)
      ? PN_CFG.menuPanels
      : [
          '/static/assets/menu-0.avif',
          '/static/assets/menu-1.avif',
          '/static/assets/menu-2.avif',
          '/static/assets/menu-3.avif',
          '/static/assets/menu-4.avif'
        ];

    const count = panelUrls.length;
    const arcSpan = (2 * Math.PI) / count - 0.035;
    const texLoader = new THREE.TextureLoader();

    panelUrls.forEach((url, idx) => {
      const geo = new THREE.CylinderGeometry(
        2.15,
        2.15,
        2.85,
        36,
        1,
        true,
        (idx * Math.PI * 2) / count - arcSpan / 2,
        arcSpan
      );
      const mat = new THREE.MeshBasicMaterial({
        color: 0x163f63,
        side: THREE.FrontSide,
        toneMapped: false
      });
      cylGroup.add(new THREE.Mesh(geo, mat));

      texLoader.load(url, tex => {
        const img = tex.image;
        const targetAspect = (2.15 * arcSpan) / 2.85;
        const imgAspect = img.width / img.height;
        if (imgAspect > targetAspect) {
          tex.repeat.x = targetAspect / imgAspect;
          tex.offset.x = (1 - tex.repeat.x) / 2;
        } else {
          tex.repeat.y = imgAspect / targetAspect;
          tex.offset.y = (1 - tex.repeat.y) / 2;
        }
        tex.colorSpace = THREE.SRGBColorSpace;
        tex.anisotropy = 4;
        mat.map = tex;
        mat.color.set(0xe2e2e2);
        mat.needsUpdate = true;
      });
    });

    const noiseTex = createRingNoiseTexture(128);
    const ringGeo = new THREE.CylinderGeometry(3.01, 2.58, 0, 128, 1, true);
    const ringMat = createCometRingMaterial({ noiseTex, isLight: false, full: 1, alpha: 0.85 });
    const ringMesh = new THREE.Mesh(ringGeo, ringMat);
    ringMesh.rotation.z = 0.06;
    rootGroup.add(ringMesh);

    const composer = new EffectComposer(renderer);
    composer.addPass(new RenderPass(scene, camera));
    const menuBloomPass = createAlphaBloomPass(0.55, 0.35, 0.93);
    composer.addPass(menuBloomPass);
    composer.addPass(new OutputPass());

    function resize() {
      const host = canvas.parentElement;
      if (!host) return;
      const w = host.clientWidth;
      const h = host.clientHeight;
      if (!w || !h) return;
      renderer.setSize(w, h, false);
      composer.setSize(w, h);
      menuBloomPass.setSize(Math.max(48, Math.floor(w * 0.55)), Math.max(48, Math.floor(h * 0.55)));
      camera.aspect = w / h;
      camera.position.z = Math.max(9.6, 16 / camera.aspect);
      camera.updateProjectionMatrix();
    }
    new ResizeObserver(resize).observe(canvas.parentElement || canvas);
    resize();

    let ptrX = 0;
    let ptrY = 0;
    window.addEventListener(
      'pointermove',
      e => {
        if (!isOpen) return;
        ptrX = e.clientX / window.innerWidth - 0.5;
        ptrY = e.clientY / window.innerHeight - 0.5;
      },
      { passive: true }
    );

    let activeIndex = 0;
    let yawAngle = 0;
    const startMs = performance.now();
    let prevMs = startMs;
    let isOpen = false;
    let rafId = 0;

    // Bind nav hover/focus to rotate cylinder panels to active menu item
    const navItems = menuDialog ? Array.from(menuDialog.querySelectorAll('#g2-menu-primary > li')) : [];
    navItems.forEach((li, idx) => {
      li.addEventListener('mouseenter', () => {
        activeIndex = idx;
      });
      const target = li.querySelector('a, button');
      if (target) {
        target.addEventListener('focus', () => {
          activeIndex = idx;
        });
      }
    });

    function animate(now) {
      if (!isOpen || document.visibilityState !== 'visible') {
        rafId = 0;
        return;
      }
      rafId = requestAnimationFrame(animate);
      const dt = Math.min(0.05, (now - prevMs) / 1000);
      prevMs = now;
      const elapsed = (now - startMs) / 1000;

      let targetYaw = -activeIndex * ((2 * Math.PI) / count);
      while (targetYaw - yawAngle > Math.PI) targetYaw -= 2 * Math.PI;
      while (targetYaw - yawAngle < -Math.PI) targetYaw += 2 * Math.PI;
      yawAngle += (targetYaw - yawAngle) * Math.min(1, 5 * dt);

      cylGroup.rotation.y = yawAngle + 0.06 * Math.sin(0.45 * elapsed);
      ringMesh.rotation.y = -elapsed * 0.45;
      ringMat.uniforms.uTime.value = 0.5 * elapsed;

      rootGroup.rotation.y += (0.3 * ptrX - rootGroup.rotation.y) * 0.04;
      rootGroup.rotation.x += (-0.1 + 0.16 * ptrY - rootGroup.rotation.x) * 0.04;

      composer.render();
    }

    document.addEventListener('visibilitychange', () => {
      if (isOpen && document.visibilityState === 'visible' && !rafId) {
        prevMs = performance.now();
        rafId = requestAnimationFrame(animate);
      }
    });

    return {
      setOpen(open) {
        isOpen = open;
        if (open) {
          resize();
          if (!rafId && document.visibilityState === 'visible') {
            prevMs = performance.now();
            rafId = requestAnimationFrame(animate);
          }
        }
      }
    };
  }

  function ensureMenuController() {
    if (menuController || menuInitStarted) return menuController;
    const menuCanvas = document.getElementById('g2-menu-canvas');
    if (!menuCanvas) return null;
    menuInitStarted = true;
    menuController = initMenuThreeJS(menuCanvas);
    return menuController;
  }

  // =========================================================================
  // 10. MASTER SCROLL ENGINE (rAF-Coalesced, Batched Reads -> Writes, Culled)
  // =========================================================================
  const scrollCache = {
    vw: window.innerWidth || 1440,
    vh: window.innerHeight || 900,
    storyTravel: 1,
    towerTravel: 1,
    dayNightTravel: 1,
    amenitiesLen: 10851
  };

  // Pre-query section inner nodes once (zero DOM queries during scroll)
  const storySticky = storySection ? storySection.querySelector('.sticky') : null;
  const storyPhase1 = storySticky ? storySticky.querySelector('.z-30.flex.flex-col.justify-between') : null;
  const storySvg = storySticky ? (document.getElementById('g2-story-mark-svg') || storySticky.querySelector('svg[viewBox^="-341"]')) : null;
  const storyMaskG = storySvg ? storySvg.querySelector('mask g') : null;
  const storyStrokeG = storySvg ? storySvg.querySelector('svg > g') : null;
  const storyFoundation = storySticky ? storySticky.querySelector('.z-30.grid') : null;

  const portfolioParallaxCards = portfolioSection
    ? Array.from(portfolioSection.querySelectorAll('figure > div.relative.overflow-hidden')).map((el, i) => ({
        el,
        factor: i % 3 === 0 ? -22 : i % 3 === 1 ? -36 : -28
      }))
    : [];

  const towerTargets = (Array.isArray(HOME_DATA?.towerTargets) && HOME_DATA.towerTargets.length === 4)
    ? HOME_DATA.towerTargets
    : [21, 6, 4, 6];
  const towerCards = towerSection
    ? Array.from(towerSection.querySelectorAll('.z-20 > div.min-w-0')).map((card, idx) => ({
        card,
        numSpan: card.querySelector('.tabular-nums > span'),
        target: towerTargets[idx] ?? 0,
        lastVal: ''
      }))
    : [];

  const amenitiesOl = amenitiesSection ? amenitiesSection.querySelector('ol') : null;
  const amenitiesPath = amenitiesOl ? amenitiesOl.querySelector('svg path') : null;
  if (amenitiesOl) {
    if (amenitiesPath) amenitiesPath.style.strokeDasharray = `${scrollCache.amenitiesLen}px`;
    amenitiesOl.querySelectorAll('li > div').forEach(div => {
      div.style.opacity = '1';
      div.style.transform = 'none';
    });
  }

  const interiorsCards = interiorsSection
    ? Array.from(interiorsSection.querySelectorAll('.flex-1 > div > div.relative')).map(card => ({
        card,
        innerImgWrap: card.querySelector('figure > div.absolute'),
        loupes: Array.from(card.querySelectorAll(':scope > span.rounded-full'))
      }))
    : [];

  const emblemPaths = emblemSection
    ? Array.from(emblemSection.querySelectorAll('svg path[stroke^="url"]')).map(path => {
        path.style.strokeDasharray = '1645.38px';
        return path;
      })
    : [];
  const emblemCircle = emblemSection ? emblemSection.querySelector('svg circle') : null;
  if (emblemCircle) emblemCircle.style.strokeDasharray = '1167.56px';

  const dayNightSec = dayNightWrapper ? dayNightWrapper.querySelector('section') : null;
  const dayNightFrame = dayNightSec ? dayNightSec.querySelector('[data-plate="true"] > div') : null;
  const dayNightLayers = dayNightFrame ? Array.from(dayNightFrame.querySelectorAll('.g2-bg')) : [];

  const ctaOuter = ctaSection ? ctaSection.firstElementChild : null;
  const ctaInner = ctaOuter ? ctaOuter.firstElementChild : null;
  if (ctaOuter) {
    ctaOuter.style.opacity = '1';
    ctaOuter.style.transform = 'none';
  }

  function measureScrollMetrics() {
    scrollCache.vh = window.innerHeight || 900;
    scrollCache.vw = window.innerWidth || 1440;
    const vh = scrollCache.vh;
    if (storySection) scrollCache.storyTravel = Math.max(1, storySection.offsetHeight - vh);
    if (towerSection) scrollCache.towerTravel = Math.max(1, towerSection.offsetHeight - vh);
    if (dayNightSec) scrollCache.dayNightTravel = Math.max(1, dayNightSec.offsetHeight - vh);
  }
  measureScrollMetrics();

  let lastScrolledPast24 = null;
  let scrollForceAll = true;
  let scrollRafId = 0;

  const sectionActiveState = {
    story: true,
    portfolio: true,
    tower: true,
    amenities: true,
    interiors: true,
    emblem: true,
    daynight: true,
    cta: true
  };

  function runScrollFrame() {
    scrollRafId = 0;
    const force = scrollForceAll;
    scrollForceAll = false;

    // -----------------------------------------------------------------------
    // PHASE 1: BATCHED LAYOUT READS (zero style writes during this phase)
    // -----------------------------------------------------------------------
    const scrollY = window.scrollY || window.pageYOffset;
    const vh = scrollCache.vh;
    const margin = 140;

    const storyRect = storySection ? storySection.getBoundingClientRect() : null;
    const portfolioRect = portfolioSection ? portfolioSection.getBoundingClientRect() : null;
    const towerRect = towerSection ? towerSection.getBoundingClientRect() : null;
    const amenitiesRect = amenitiesOl ? amenitiesOl.getBoundingClientRect() : null;
    const interiorsRect = interiorsSection ? interiorsSection.getBoundingClientRect() : null;
    const emblemRect = emblemSection ? emblemSection.getBoundingClientRect() : null;
    const dayNightRect = dayNightSec ? dayNightSec.getBoundingClientRect() : null;
    const ctaRect = ctaSection ? ctaSection.getBoundingClientRect() : null;

    const headingReads = displayHeadingStates.map(state => ({
      state,
      rect: state.h2.getBoundingClientRect()
    }));

    const interiorsInRange = Boolean(interiorsRect && (interiorsRect.top < vh + margin && interiorsRect.bottom > -margin));
    const interiorCardReads = (interiorsInRange || force)
      ? interiorsCards.map(item => ({ item, rect: item.card.getBoundingClientRect() }))
      : [];

    // -----------------------------------------------------------------------
    // PHASE 2: BATCHED STYLE WRITES (no layout reads interleaved)
    // -----------------------------------------------------------------------
    const past24 = scrollY > 24;
    if (headerBlur && past24 !== lastScrolledPast24) {
      lastScrolledPast24 = past24;
      headerBlur.classList.toggle('opacity-100', past24);
      headerBlur.classList.toggle('opacity-0', !past24);
    }

    if (window.__updateHeroScroll && (scrollY <= vh * 2.2 || force)) {
      window.__updateHeroScroll(scrollY);
    }

    if (storyRect && storySticky) {
      const inRange = storyRect.top < vh + margin && storyRect.bottom > -margin;
      if (inRange || sectionActiveState.story || force) {
        sectionActiveState.story = inRange;
        const p = clamp01(-storyRect.top / scrollCache.storyTravel);
        const p1 = clamp01(p / 0.42);
        if (storyPhase1) {
          storyPhase1.style.opacity = (1 - p1).toFixed(4);
          storyPhase1.style.transform = `translate3d(0, ${(-24 * p1).toFixed(2)}px, 0)`;
        }
        const scale = 1 + Math.pow(p, 2.35) * 28;
        const transformStr = `scale(${scale.toFixed(4)}) rotate(${(p * 360).toFixed(2)}deg)`;
        if (storyMaskG) storyMaskG.style.transform = transformStr;
        if (storyStrokeG) storyStrokeG.style.transform = transformStr;
        if (storySvg) {
          storySvg.style.opacity = (p > 0.78 ? clamp01(1 - (p - 0.78) / 0.18) : 1).toFixed(4);
        }
        const p2 = clamp01((p - 0.48) / 0.3);
        if (storyFoundation) {
          storyFoundation.style.opacity = p2.toFixed(4);
          storyFoundation.style.transform = p2 >= 0.99 ? 'none' : `translate3d(0, ${(26 * (1 - p2)).toFixed(2)}px, 0)`;
        }
      }
    }

    headingReads.forEach(({ state, rect }) => {
      const p = clamp01((vh * 0.95 - rect.top) / (vh * 0.6));
      if (!force && Math.abs(p - state.lastP) < 0.0005) return;
      state.lastP = p;
      const isAnimating = p > 0.001 && p < 0.995;
      const total = state.letters.length || 1;
      state.letters.forEach((el, i) => {
        const delay = (i / total) * 0.28;
        const lp = clamp01((p - delay) / 0.72);
        el.style.willChange = isAnimating && lp < 0.995 ? 'transform' : 'auto';
        el.style.transform =
          lp >= 0.995
            ? 'none'
            : `translate3d(0, ${((1 - lp) * 100).toFixed(2)}%, 0) rotateX(${((1 - lp) * 52).toFixed(2)}deg)`;
      });
    });

    if (portfolioRect && portfolioParallaxCards.length) {
      const inRange = portfolioRect.top < vh + margin && portfolioRect.bottom > -margin;
      if (inRange || sectionActiveState.portfolio || force) {
        sectionActiveState.portfolio = inRange;
        const p = clamp01((vh - portfolioRect.top) / (vh + portfolioRect.height));
        portfolioParallaxCards.forEach(({ el, factor }) => {
          el.style.transform = `translate3d(0, ${(factor * p).toFixed(2)}px, 0)`;
        });
      }
    }

    if (towerRect) {
      const inRange = towerRect.top < vh + margin && towerRect.bottom > -margin;
      if (inRange || sectionActiveState.tower || force) {
        sectionActiveState.tower = inRange;
        const p = clamp01(-towerRect.top / scrollCache.towerTravel);
        const enterP = clamp01((vh * 0.75 - towerRect.top) / (vh * 0.65));

        if (towerController) {
          towerController.setProgress(p);
          towerController.setBackdropOpacity(clamp01((towerRect.bottom / vh - 0.55) / 0.42));
        }

        towerCards.forEach((item, idx) => {
          const cp = clamp01((enterP - idx * 0.12) / 0.55);
          item.card.style.opacity = cp.toFixed(4);
          item.card.style.transform = cp >= 0.99 ? 'none' : `translate3d(0, ${(-18 * (1 - cp)).toFixed(2)}px, 0)`;
          const valStr = String(Math.round(item.target * cp));
          if (item.numSpan && valStr !== item.lastVal) {
            item.lastVal = valStr;
            item.numSpan.textContent = valStr;
          }
        });
      }
    }

    if (amenitiesRect && amenitiesPath) {
      const inRange = amenitiesRect.top < vh + margin && amenitiesRect.bottom > -margin;
      if (inRange || sectionActiveState.amenities || force) {
        sectionActiveState.amenities = inRange;
        const p = clamp01((vh * 0.75 - amenitiesRect.top) / (amenitiesRect.height + vh * 0.25));
        amenitiesPath.style.strokeDashoffset = `${(scrollCache.amenitiesLen * (1 - p)).toFixed(1)}px`;
      }
    }

    if (interiorCardReads.length || (interiorsSection && sectionActiveState.interiors && !interiorsInRange)) {
      sectionActiveState.interiors = interiorsInRange;
      interiorCardReads.forEach(({ item, rect }) => {
        const p = clamp01((vh * 0.95 - rect.top) / (vh * 0.55));
        item.card.style.opacity = Math.max(0.85, p).toFixed(4);
        item.card.style.transform = p >= 0.99 ? 'translate3d(0, 0vh, 0)' : `translate3d(0, ${((1 - p) * 6).toFixed(2)}vh, 0)`;
        const scrollRatio = clamp01((vh - rect.top) / (vh + rect.height));
        if (item.innerImgWrap) {
          item.innerImgWrap.style.transform = `translate3d(0, ${(-6 * scrollRatio).toFixed(2)}%, 0)`;
        }
        item.loupes.forEach((loupe, li) => {
          const y = li === 0 ? 18 * (1 - scrollRatio * 0.7) : -26 * scrollRatio;
          loupe.style.transform = `translate3d(0, ${y.toFixed(1)}px, 0)`;
        });
      });
    }

    if (emblemRect) {
      const inRange = emblemRect.top < vh + margin && emblemRect.bottom > -margin;
      if (inRange || sectionActiveState.emblem || force) {
        sectionActiveState.emblem = inRange;
        const p = clamp01((vh * 0.9 - emblemRect.top) / (vh * 0.65));
        emblemPaths.forEach(path => {
          path.style.strokeDashoffset = `${(1645.38 * (1 - p)).toFixed(2)}px`;
        });
        if (emblemCircle) {
          emblemCircle.style.strokeDashoffset = `${(1167.56 * (1 - p)).toFixed(2)}px`;
        }
      }
    }

    if (dayNightRect && dayNightFrame) {
      const inRange = dayNightRect.top < vh + margin && dayNightRect.bottom > -margin;
      if (inRange || sectionActiveState.daynight || force) {
        sectionActiveState.daynight = inRange;
        const p = clamp01(-dayNightRect.top / scrollCache.dayNightTravel);
        const expandP = clamp01(p / 0.22);
        dayNightFrame.style.clipPath = `inset(0% ${(6 * (1 - expandP)).toFixed(2)}% round ${(56 * (1 - expandP)).toFixed(1)}px)`;

        const stage = p * (dayNightLayers.length - 1);
        const opacities = dayNightLayers.map((_, idx) => (idx === 0 ? 1 : clamp01(stage - (idx - 1))));
        let topOpaqueIdx = 0;
        for (let i = 0; i < opacities.length; i++) {
          if (opacities[i] >= 0.999) topOpaqueIdx = i;
        }
        dayNightLayers.forEach((layer, idx) => {
          const op = opacities[idx];
          const hidden = idx < topOpaqueIdx || op <= 0.001;
          layer.style.visibility = hidden ? 'hidden' : 'visible';
          layer.style.opacity = hidden ? '0' : op.toFixed(4);
        });
      }
    }

    if (ctaRect && ctaInner) {
      const inRange = ctaRect.top < vh + margin && ctaRect.bottom > -margin;
      if (inRange || sectionActiveState.cta || force) {
        sectionActiveState.cta = inRange;
        const p = clamp01((vh - ctaRect.top) / (vh + ctaRect.height));
        ctaInner.style.transform = `translate3d(0, ${(70 - p * 22).toFixed(2)}px, 0)`;
      }
    }
  }

  function scheduleScrollUpdate(isResize = false) {
    if (isResize) {
      measureScrollMetrics();
      scrollForceAll = true;
    }
    if (!scrollRafId) {
      scrollRafId = requestAnimationFrame(runScrollFrame);
    }
  }

  window.addEventListener('scroll', () => scheduleScrollUpdate(false), { passive: true });
  window.addEventListener('resize', () => scheduleScrollUpdate(true), { passive: true });
  runScrollFrame();

  // =========================================================================
  // 11. PRO PLATFORM INTERACTIVE UTILITIES (DIALOGS, ARIA FORMS, EMI, LIGHTBOX)
  // =========================================================================

  // A. Native <dialog> light-dismiss fallback for browsers without closedby="any"
  function attachDialogLightDismiss(dialog) {
    if (!dialog || dialog.dataset.pnDismissWired) return;
    dialog.dataset.pnDismissWired = '1';
    if (!('closedBy' in HTMLDialogElement.prototype)) {
      dialog.addEventListener('click', event => {
        if (event.target !== dialog) return;
        const rect = dialog.getBoundingClientRect();
        const inside =
          rect.top <= event.clientY &&
          event.clientY <= rect.top + rect.height &&
          rect.left <= event.clientX &&
          event.clientX <= rect.left + rect.width;
        if (!inside) dialog.close();
      });
    }
  }
  document.querySelectorAll('dialog[closedby]').forEach(attachDialogLightDismiss);
  document.addEventListener('click', e => {
    const opener = e.target.closest?.('[data-open-dialog]');
    if (!opener) return;
    const dlg = document.getElementById(opener.dataset.openDialog);
    if (dlg) {
      attachDialogLightDismiss(dlg);
      if (opener.dataset.dialogField && opener.dataset.dialogValue !== undefined) {
        const inp = dlg.querySelector(`[name="${opener.dataset.dialogField}"]`);
        if (inp) inp.value = opener.dataset.dialogValue;
      }
      if (opener.dataset.dialogAction) {
        const frm = dlg.querySelector('form');
        if (frm) frm.action = opener.dataset.dialogAction;
      }
      dlg.showModal();
    }
  });
  document.addEventListener('click', e => {
    const closer = e.target.closest?.('[data-close-dialog]');
    if (!closer) return;
    const dlg = closer.closest('dialog');
    if (dlg) dlg.close();
  });

  // B. Universal Confirmation <dialog> for destructive POST actions
  const confirmDialog = document.getElementById('pn-confirm-dialog');
  if (confirmDialog) {
    attachDialogLightDismiss(confirmDialog);
    const confirmForm = confirmDialog.querySelector('form[data-confirm-form]');
    const confirmTitle = confirmDialog.querySelector('[data-confirm-title]');
    const confirmBody = confirmDialog.querySelector('[data-confirm-body]');
    const confirmNoteWrap = confirmDialog.querySelector('[data-confirm-note-wrap]');
    const confirmNoteInput = confirmDialog.querySelector('[data-confirm-note]');
    const confirmSubmitBtn = confirmDialog.querySelector('[data-confirm-submit]');

    document.addEventListener('click', e => {
      const trigger = e.target.closest?.('[data-confirm-action]');
      if (!trigger || !confirmForm) return;
      e.preventDefault();
      confirmForm.action = trigger.dataset.confirmAction;
      if (confirmTitle) confirmTitle.textContent = trigger.dataset.confirmTitle || 'Confirm Action';
      if (confirmBody) confirmBody.textContent = trigger.dataset.confirmBody || 'Are you sure you want to proceed?';
      if (confirmSubmitBtn) {
        confirmSubmitBtn.textContent = trigger.dataset.confirmLabel || 'Confirm';
        confirmSubmitBtn.className = trigger.dataset.confirmVariant === 'primary'
          ? 'pn-btn pn-btn-primary'
          : 'pn-btn pn-btn-danger';
      }
      if (confirmNoteWrap) {
        const showNote = trigger.dataset.confirmShowNote === 'true';
        confirmNoteWrap.hidden = !showNote;
        if (confirmNoteInput) confirmNoteInput.value = '';
      }
      confirmDialog.showModal();
    });
  }

  // C. Property Lightbox Gallery Modal
  const lightboxDialog = document.getElementById('pn-lightbox-dialog');
  if (lightboxDialog) {
    attachDialogLightDismiss(lightboxDialog);
    const lbImg = lightboxDialog.querySelector('[data-lightbox-img]');
    const lbCounter = lightboxDialog.querySelector('[data-lightbox-counter]');
    const lbTriggers = Array.from(document.querySelectorAll('[data-lightbox-src]'));
    let lbIndex = 0;

    function showLightbox(idx) {
      if (!lbTriggers.length || !lbImg) return;
      lbIndex = (idx + lbTriggers.length) % lbTriggers.length;
      const item = lbTriggers[lbIndex];
      lbImg.src = item.dataset.lightboxSrc;
      lbImg.alt = item.dataset.lightboxAlt || 'Property view';
      if (lbCounter) lbCounter.textContent = `${lbIndex + 1} / ${lbTriggers.length}`;
    }

    lbTriggers.forEach((btn, idx) => {
      btn.addEventListener('click', () => {
        showLightbox(idx);
        lightboxDialog.showModal();
      });
    });

    lightboxDialog.querySelector('[data-lightbox-prev]')?.addEventListener('click', () => showLightbox(lbIndex - 1));
    lightboxDialog.querySelector('[data-lightbox-next]')?.addEventListener('click', () => showLightbox(lbIndex + 1));
    lightboxDialog.addEventListener('keydown', e => {
      if (e.key === 'ArrowLeft') showLightbox(lbIndex - 1);
      if (e.key === 'ArrowRight') showLightbox(lbIndex + 1);
    });
  }

  // D. Accessible Form Validation: :user-invalid fallback + aria-invalid / aria-describedby + aria-live announcer
  (function initAccessibleForms() {
    const forms = document.querySelectorAll('form.pn-validated-form');
    if (!forms.length) return;

    const announcer = document.createElement('div');
    announcer.setAttribute('aria-live', 'polite');
    announcer.className = 'visually-hidden';
    document.body.append(announcer);
    let announceTimer;

    const linkError = (el, shown) => {
      const errorId = el.dataset.error;
      if (!errorId) return;
      const ids = (el.getAttribute('aria-describedby') || '').split(/\s+/).filter(id => id && id !== errorId);
      if (shown) ids.push(errorId);
      if (ids.length) el.setAttribute('aria-describedby', ids.join(' '));
      else el.removeAttribute('aria-describedby');
    };

    const supportsUserInvalid = typeof CSS !== 'undefined' && CSS.supports?.('selector(:user-invalid)');
    const dirtyState = new WeakMap();

    const syncField = (el, announce = false) => {
      if (!el?.matches?.('input, select, textarea') || el.type === 'hidden') return;
      const isValid = el.validity.valid;
      let isShownInvalid = supportsUserInvalid ? el.matches(':user-invalid') : false;

      if (!supportsUserInvalid) {
        const st = dirtyState.get(el);
        isShownInvalid = Boolean(st?.hasBlurred && !isValid);
        el.classList.toggle('user-invalid-fallback', isShownInvalid);
        el.classList.toggle('user-valid-fallback', Boolean(st?.hasBlurred && isValid));
      }

      if (isShownInvalid) {
        el.setAttribute('aria-invalid', 'true');
        linkError(el, true);
        if (announce && el.dataset.error) {
          const errEl = document.getElementById(el.dataset.error);
          if (errEl) {
            clearTimeout(announceTimer);
            announceTimer = setTimeout(() => {
              announcer.textContent = errEl.textContent.replace(/\s+/g, ' ').trim();
            }, 400);
          }
        }
      } else {
        el.setAttribute('aria-invalid', 'false');
        linkError(el, false);
      }
    };

    forms.forEach(form => {
      form.querySelectorAll('input, select, textarea').forEach(el => {
        if (el.type !== 'hidden' && !el.hasAttribute('aria-invalid')) {
          el.setAttribute('aria-invalid', 'false');
        }
      });

      form.addEventListener('blur', e => {
        const st = dirtyState.get(e.target) || { hasInteracted: true, hasBlurred: false };
        st.hasBlurred = true;
        dirtyState.set(e.target, st);
        syncField(e.target, true);
      }, true);

      form.addEventListener('input', e => {
        const st = dirtyState.get(e.target) || { hasInteracted: false, hasBlurred: false };
        st.hasInteracted = true;
        dirtyState.set(e.target, st);
        if (e.target.hasAttribute('aria-invalid')) syncField(e.target, false);
      });

      form.addEventListener('invalid', e => {
        dirtyState.set(e.target, { hasInteracted: true, hasBlurred: true });
        syncField(e.target, false);
      }, true);
    });
  })();

  // E. Interactive Password Visibility Toggles
  document.addEventListener('click', e => {
    const btn = e.target.closest?.('[data-password-toggle]');
    if (!btn) return;
    const input = document.getElementById(btn.dataset.passwordToggle);
    if (!input) return;
    const showing = input.type === 'text';
    input.type = showing ? 'password' : 'text';
    btn.setAttribute('aria-pressed', showing ? 'false' : 'true');
    btn.setAttribute('aria-label', showing ? 'Show password' : 'Hide password');
    const lbl = btn.querySelector('[data-pw-label]');
    if (lbl) lbl.textContent = showing ? 'Show' : 'Hide';
  });

  // F. Toast Notifications Dismiss & Auto-Dismiss
  document.querySelectorAll('[data-toast]').forEach(toast => {
    const closeBtn = toast.querySelector('[data-toast-close]');
    const dismiss = () => {
      toast.style.transition = 'opacity 250ms ease, transform 250ms ease';
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(-8px)';
      setTimeout(() => toast.remove(), 260);
    };
    closeBtn?.addEventListener('click', dismiss);
    setTimeout(dismiss, 6500);
  });

  // G. Property Detail Interactive Mortgage / EMI Calculator
  const emiRoot = document.querySelector('[data-emi-calc]');
  if (emiRoot) {
    const price = parseFloat(emiRoot.dataset.price || '0');
    const downEl = emiRoot.querySelector('[data-emi-down]');
    const rateEl = emiRoot.querySelector('[data-emi-rate]');
    const yearsEl = emiRoot.querySelector('[data-emi-years]');
    const outMonthly = emiRoot.querySelector('[data-emi-monthly]');
    const outDownAmt = emiRoot.querySelector('[data-emi-down-val]');
    const outLoan = emiRoot.querySelector('[data-emi-loan]');
    const outRateVal = emiRoot.querySelector('[data-emi-rate-val]');
    const outYearsVal = emiRoot.querySelector('[data-emi-years-val]');

    const updateEmi = () => {
      if (!price) return;
      const downPct = parseFloat(downEl?.value || '20');
      const annualRate = parseFloat(rateEl?.value || '8.5');
      const years = parseInt(yearsEl?.value || '20', 10);

      const downAmount = price * (downPct / 100);
      const principal = Math.max(0, price - downAmount);
      const monthlyRate = annualRate / 12 / 100;
      const months = years * 12;

      let emi = 0;
      if (monthlyRate > 0 && months > 0) {
        const f = Math.pow(1 + monthlyRate, months);
        emi = (principal * monthlyRate * f) / (f - 1);
      } else if (months > 0) {
        emi = principal / months;
      }

      const fmt = n => '$' + Math.round(n).toLocaleString('en-US');
      if (outDownAmt) outDownAmt.textContent = `${downPct}% (${fmt(downAmount)})`;
      if (outRateVal) outRateVal.textContent = `${annualRate.toFixed(1)}%`;
      if (outYearsVal) outYearsVal.textContent = `${years} yrs`;
      if (outLoan) outLoan.textContent = fmt(principal);
      if (outMonthly) outMonthly.textContent = fmt(emi);
    };

    [downEl, rateEl, yearsEl].forEach(el => el?.addEventListener('input', updateEmi));
    updateEmi();
  }

  // H. Asynchronous Save / Wishlist Button Enhancement
  document.addEventListener('submit', async e => {
    const form = e.target.closest?.('form[data-ajax-save]');
    if (!form) return;
    e.preventDefault();
    const btn = form.querySelector('button[type="submit"]');
    try {
      const res = await fetch(form.action, {
        method: 'POST',
        body: new FormData(form),
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
        credentials: 'same-origin'
      });
      if (res.redirected && res.url.includes('/login')) {
        window.location.href = res.url;
        return;
      }
      if (!res.ok) {
        form.submit();
        return;
      }
      const data = await res.json();
      if (btn) {
        btn.setAttribute('aria-pressed', data.saved ? 'true' : 'false');
        const label = btn.querySelector('[data-save-label]');
        if (label) label.textContent = data.saved ? 'Saved Residence' : 'Save Residence';
        const icon = btn.querySelector('[data-save-icon]');
        if (icon) icon.textContent = data.saved ? '♥' : '♡';
        btn.classList.toggle('pn-btn-primary', Boolean(data.saved));
      }
      const badge = document.querySelector('[data-nav-saved-count]');
      if (badge && typeof data.saved_count === 'number') {
        badge.textContent = String(data.saved_count);
      }
    } catch (_) {
      form.submit();
    }
  });
})();
