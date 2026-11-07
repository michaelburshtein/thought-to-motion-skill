// Example: a score counts up to its real value, the meter and category bars fill,
// the verdict, chips and closing line land. Use with animate_slide.py --dur 6.
window.__setup = () => {
  window.S = { big: $('.score b'), meter: $('.meter i'), st: $$('.status'), chips: $$('.chips .chip'),
               rows: $$('.rows .row'), bars: $$('.rows .row .m i') };
  S.barW = S.bars.map(b => parseFloat(b.style.width)); S.final = parseInt(S.big.textContent, 10);
};
window.__t = t => {
  const k = win(t, 0.3, 1.9);
  S.big.textContent = Math.round(S.final * k); S.meter.style.width = (S.final * k) + '%';
  const s0 = win(t, 1.9, 2.3); S.st[0].style.opacity = s0; S.st[0].style.transform = `translateY(${(1 - s0) * 16}px)`;
  S.chips.forEach((c, i) => { const v = win(t, 2.2 + i * .15, 2.5 + i * .15); c.style.opacity = v; c.style.transform = `scale(${.85 + .15 * v})`; });
  S.rows.forEach((r, i) => { const v = win(t, 2.6 + i * .25, 2.9 + i * .25); r.style.opacity = v; r.style.transform = `translateX(${(1 - v) * -20}px)`; });
  S.bars.forEach((b, i) => { b.style.width = (S.barW[i] * win(t, 2.8 + i * .25, 3.6 + i * .25)) + '%'; });
  if (S.st[1]) { const s1 = win(t, 3.9, 4.3); S.st[1].style.opacity = s1; S.st[1].style.transform = `translateY(${(1 - s1) * 16}px)`; }
};
