const available = document.querySelectorAll('.table.available');
const selNum    = document.getElementById('selected-number');
const dtIn      = document.getElementById('datetime');
const btn       = document.getElementById('reserve-btn');
const form      = document.getElementById('reserve-form');
const fTables   = document.getElementById('f-tables');

let chosen = [];

function updateFormState() {
  fTables.value = chosen.join(',');
  btn.disabled = !(chosen.length > 0 && dtIn.value.trim());
  selNum.textContent = chosen.length ? chosen.join(', ') : '—';
}

available.forEach(el => {
  el.addEventListener('click', () => {
    const n = el.dataset.table;
    el.classList.toggle('selected');
    if (el.classList.contains('selected')) {
      if (!chosen.includes(n)) chosen.push(n);
    } else {
      chosen = chosen.filter(x => x !== n);
    }
    updateFormState();
  });
});

dtIn.addEventListener('input', updateFormState);

form.addEventListener('submit', (e) => {
  updateFormState();
  if (btn.disabled) {
    e.preventDefault();
    alert("Заповніть всі поля перед підтвердженням.");
  }
});
