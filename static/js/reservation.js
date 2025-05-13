const available = document.querySelectorAll('.table.available');
const selNum    = document.getElementById('selected-number');
const dtIn      = document.getElementById('datetime');
const btn       = document.getElementById('reserve-btn');
const form      = document.getElementById('reserve-form');
const fTables   = document.getElementById('f-tables');
const fDt       = document.getElementById('f-dt');
let chosen = [];

available.forEach(el=>{
  el.onclick = ()=>{
    const n = el.dataset.table;
    if(el.classList.toggle('selected')){
      chosen.push(n);
    } else {
      chosen = chosen.filter(x=>x!==n);
    }
    selNum.textContent = chosen.join(',')||'—';
    fTables.value = chosen.join(',');
    toggleBtn();
  };
});

dtIn.onchange = ()=>{
  fDt.value = dtIn.value;
  toggleBtn();
};
function toggleBtn(){
  btn.disabled = !(chosen.length && dtIn.value);
}
btn.onclick = e=>{
  e.preventDefault();
  form.submit();
};