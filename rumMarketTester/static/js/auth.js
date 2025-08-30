// CSRF from cookie
function getCookie(name){
  const m = document.cookie.match(new RegExp('(^|; )' + name + '=([^;]+)'));
  return m ? decodeURIComponent(m[2]) : '';
}
function post(url, data){
  return fetch(url, {
    method: 'POST',
    headers: {'X-CSRFToken': getCookie('csrftoken')},
    body: new URLSearchParams(data)
  });
}
const loginModal = document.getElementById('loginModal');
const signupModal = document.getElementById('signupModal');
function openModal(m){ m.classList.remove('hidden'); }
function closeModals(){ document.querySelectorAll('.modal').forEach(x=>x.classList.add('hidden')); }
document.getElementById('loginOpen')?.addEventListener('click', ()=>openModal(loginModal));
document.getElementById('signupOpen')?.addEventListener('click', ()=>openModal(signupModal));
document.querySelectorAll('[data-close]').forEach(b=>b.addEventListener('click', closeModals));

document.getElementById('loginForm')?.addEventListener('submit', async (e)=>{
  e.preventDefault();
  const r = await post('/accounts/login-json/', Object.fromEntries(new FormData(e.target)));
  if (r.ok) location.reload(); else document.getElementById('loginErr').textContent = 'Invalid credentials';
});
document.getElementById('signupForm')?.addEventListener('submit', async (e)=>{
  e.preventDefault();
  const r = await post('/accounts/signup-json/', Object.fromEntries(new FormData(e.target)));
  if (r.ok) location.reload(); else document.getElementById('signupErr').textContent = 'Please check fields';
});
document.getElementById('logoutBtn')?.addEventListener('click', async ()=>{
  await post('/accounts/logout-json/', {}); location.reload();
});
