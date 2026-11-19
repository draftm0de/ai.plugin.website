// Form validation and review step for forms marked with data-validate (the messages come from the data-msg-* attributes).
// There is no send action: after a valid entry the values are shown for review; sending needs a service.
const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

function fieldLabel(el: HTMLElement): string {
  const group = el.closest('fieldset.form__choices');
  const text = (group ? group.querySelector('legend') : el.closest('.form__field')?.querySelector('label'))?.textContent ?? '';
  return text.replace('*', '').trim();
}

function problem(form: HTMLFormElement, control: HTMLElement): string {
  const msg = (key: string) => form.dataset['msg' + key.charAt(0).toUpperCase() + key.slice(1)] ?? '';
  if (control instanceof HTMLInputElement && (control.type === 'radio' || control.type === 'checkbox')) {
    const name = control.name;
    const group = form.querySelectorAll<HTMLInputElement>(`input[name="${name}"]`);
    return control.required || control.closest('[data-required]') ? ([...group].some((i) => i.checked) ? '' : msg('choose')) : '';
  }
  const value = (control as HTMLInputElement).value.trim();
  const digits = value.replace(/\D/g, '');
  if (control.hasAttribute('required') && (value === '' || (control instanceof HTMLInputElement && control.type === 'tel' && /^\+\d{1,3}$/.test(value)))) return msg('required');
  if (control instanceof HTMLInputElement && control.type === 'email' && value !== '' && !EMAIL.test(value)) return msg('email');
  if (control instanceof HTMLInputElement && control.type === 'tel' && value !== '' && !/^\+\d{1,3}$/.test(value)) {
    if (!/^\+?[0-9 ()/.\-]+$/.test(value) || digits.length < 6) return msg('phone');
  }
  return '';
}

function clearError(control: HTMLElement) {
  control.removeAttribute('aria-invalid');
  const id = control.id;
  document.getElementById(`${id}-error`)?.remove();
  const described = (control.getAttribute('aria-describedby') ?? '').split(' ').filter((x) => x && x !== `${id}-error`).join(' ');
  if (described) control.setAttribute('aria-describedby', described); else control.removeAttribute('aria-describedby');
}

function setup(form: HTMLFormElement) {
  let review: HTMLElement | null = null;
  const controls = () => [...form.querySelectorAll<HTMLElement>('input:not([type=hidden]):not(.form__trap input), select, textarea')];

  const validate = (): boolean => {
    form.querySelector('.form__summary')?.remove();
    const found: { control: HTMLElement; text: string }[] = [];
    const seen = new Set<string>();
    for (const control of controls()) {
      const input = control as HTMLInputElement;
      if (input.type === 'radio' || input.type === 'checkbox') {
        if (seen.has(input.name)) continue;
        seen.add(input.name);
      }
      clearError(control);
      const text = problem(form, control);
      if (text) found.push({ control, text });
    }
    if (found.length === 0) return true;
    for (const { control, text } of found) {
      const error = document.createElement('p');
      error.className = 'form__error';
      error.id = `${control.id}-error`;
      error.textContent = text;
      const holder = control.closest('.form__choices') ?? control;
      holder.insertAdjacentElement(holder === control ? 'afterend' : 'beforeend', error);
      control.setAttribute('aria-invalid', 'true');
      control.setAttribute('aria-describedby', [control.getAttribute('aria-describedby'), error.id].filter(Boolean).join(' '));
    }
    const summary = document.createElement('div');
    summary.className = 'form__summary';
    summary.setAttribute('role', 'alert');
    summary.tabIndex = -1;
    summary.innerHTML = `<p></p><ul></ul>`;
    summary.querySelector('p')!.textContent = form.dataset.msgSummary ?? '';
    for (const { control, text } of found) {
      const li = document.createElement('li');
      const link = document.createElement('a');
      link.href = `#${control.id}`;
      link.textContent = `${fieldLabel(control)}: ${text}`;
      link.addEventListener('click', (e) => { e.preventDefault(); control.focus(); });
      li.append(link);
      summary.querySelector('ul')!.append(li);
    }
    form.prepend(summary);
    summary.focus();
    return false;
  };

  form.addEventListener('submit', (event) => {
    event.preventDefault();
    if (form.querySelector<HTMLInputElement>('.form__trap input')?.value) return;      // filled by a robot
    if (!validate()) return;
    showReview();
  });
  form.addEventListener('input', (event) => { const t = event.target as HTMLElement; if (t.hasAttribute('aria-invalid')) clearError(t); });

  function showReview() {
    review?.remove();
    review = document.createElement('section');
    review.className = 'form__review';
    review.setAttribute('aria-labelledby', `${form.id}-review`);
    const title = document.createElement('p');
    title.className = 'form__review-title';
    title.id = `${form.id}-review`;
    title.textContent = form.dataset.msgReview ?? '';
    const list = document.createElement('dl');
    const done = new Set<string>();
    for (const control of controls()) {
      const input = control as HTMLInputElement;
      let value = input.value.trim();
      if (input.type === 'radio' || input.type === 'checkbox') {
        if (done.has(input.name)) continue;
        done.add(input.name);
        value = [...form.querySelectorAll<HTMLInputElement>(`input[name="${input.name}"]:checked`)].map((i) => i.value).join(', ');
      } else if (control instanceof HTMLSelectElement) {
        value = control.selectedOptions[0]?.textContent?.trim() ?? '';
      }
      if (!value || (input.type === 'tel' && /^\+\d{1,3}$/.test(value))) continue;
      const dt = document.createElement('dt');
      dt.textContent = fieldLabel(control);
      const dd = document.createElement('dd');
      dd.textContent = value;
      list.append(dt, dd);
    }
    const note = document.createElement('p');
    note.className = 'form__note';
    note.textContent = form.dataset.msgUnavailable ?? '';
    const actions = document.createElement('div');
    actions.className = 'form__actions';
    const back = document.createElement('button');
    back.type = 'button';
    back.className = 'form__submit';
    back.innerHTML = '<span></span>';
    back.querySelector('span')!.textContent = form.dataset.msgBack ?? '';
    back.addEventListener('click', () => { review?.remove(); form.hidden = false; (controls()[0] as HTMLElement).focus(); });
    const send = document.createElement('button');
    send.type = 'button';
    send.className = 'form__submit';
    send.disabled = true;
    send.innerHTML = '<span></span>';
    send.querySelector('span')!.textContent = form.dataset.msgSend ?? '';
    actions.append(back, send);
    review.append(title, list, note, actions);
    form.hidden = true;
    form.insertAdjacentElement('afterend', review);
    title.tabIndex = -1;
    title.focus();
  }
}

document.querySelectorAll<HTMLFormElement>('form[data-validate]').forEach(setup);
