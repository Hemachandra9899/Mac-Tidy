import { isDialogOpen, setDialogStatus } from './dialog.js';

const DURATION_MS = 6500;
let timer;

export function toast(message) {
  if (isDialogOpen()) setDialogStatus(message);
  const element = document.querySelector('#toast');
  element.textContent = message;
  element.style.display = 'block';
  clearTimeout(timer);
  timer = setTimeout(() => { element.style.display = 'none'; }, DURATION_MS);
}
