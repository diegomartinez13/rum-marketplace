const isAuth = document.body.dataset.auth === '1';
const productModal = document.getElementById('productModal');
function openProductModal(d){
  productModal.classList.remove('hidden');
  document.getElementById('pm_title').textContent = d.title;
  document.getElementById('pm_price').textContent = `$${d.price}`;
  document.getElementById('pm_desc').textContent = d.description || '';
  const ex = document.getElementById('pm_exchange');
  ex.style.display = d.exchange ? '' : 'none';
  const img = document.getElementById('pm_img');
  if (d.image){ img.src = d.image; img.style.display=''; } else { img.style.display='none'; }
}
document.querySelectorAll('.listing-link').forEach(a=>{
  a.addEventListener('click', async e=>{
    e.preventDefault();
    const id = a.dataset.id;
    if (!isAuth){ document.getElementById('loginModal').classList.remove('hidden'); return; }
    const r = await fetch(`/api/listings/${id}/`);
    if (r.status === 401){ document.getElementById('loginModal').classList.remove('hidden'); return; }
    if (r.ok){ const d = await r.json(); openProductModal(d); }
  });
});
document.querySelectorAll('#productModal [data-close]').forEach(b=>b.addEventListener('click', ()=>productModal.classList.add('hidden')));
