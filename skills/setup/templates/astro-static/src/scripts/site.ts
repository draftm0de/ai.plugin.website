import './form';
// Site-wide progressive enhancement: mobile navigation and external links.

const toggle = document.querySelector<HTMLButtonElement>('.site-header__toggle');
const nav = document.querySelector<HTMLElement>('.site-nav');

function setMenu(open: boolean) {
  if (nav) nav.dataset.open = String(open);
  document.body.toggleAttribute('data-nav-open', open);
  toggle?.setAttribute('aria-expanded', String(open));
}

toggle?.addEventListener('click', () => setMenu(nav?.dataset.open !== 'true'));
// a side menu closes with Escape and with a click outside of it
document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape' && nav?.dataset.open === 'true') { setMenu(false); toggle?.focus(); }
});
document.addEventListener('click', (event) => {
  if (nav?.dataset.open === 'true' && !nav.contains(event.target as Node) && !toggle?.contains(event.target as Node)) setMenu(false);
});

// Sub menus in the side menu open with the plus sign and close with the minus sign
document.querySelectorAll<HTMLButtonElement>('.site-nav__expand').forEach((button) => {
  button.addEventListener('click', () => {
    const open = button.getAttribute('aria-expanded') !== 'true';
    button.setAttribute('aria-expanded', String(open));
    button.closest<HTMLElement>('.site-nav__item')?.toggleAttribute('data-open', open);
  });
});

document.querySelectorAll<HTMLAnchorElement>('a[href^="http"]').forEach((link) => {
  link.target = '_blank';
  link.rel = 'noopener noreferrer';
});

// "Back to top" button: shown after scrolling one window height (only when the layout has it)
const toTop = document.querySelector<HTMLAnchorElement>('.to-top');
if (toTop) {
  const update = () => { toTop.hidden = window.scrollY < window.innerHeight / 2; };
  window.addEventListener('scroll', update, { passive: true });
  update();
}
