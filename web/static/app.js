(function(){
	const $ = (sel, root=document) => root.querySelector(sel);
	const $$ = (sel, root=document) => Array.from(root.querySelectorAll(sel));

	// Theme toggle
	const themeBtn = $('#theme-toggle');
	const THEME_KEY = 'theme';
	const applyTheme = (t) => document.documentElement.setAttribute('data-theme', t);
	const saved = localStorage.getItem(THEME_KEY);
	if (saved) applyTheme(saved);
	if (themeBtn) themeBtn.addEventListener('click', () => {
		const current = document.documentElement.getAttribute('data-theme') || 'dark';
		const next = current === 'dark' ? 'light' : 'dark';
		applyTheme(next);
		localStorage.setItem(THEME_KEY, next);
	});

	// Autocomplete
	function bindAutocomplete(inputId, panelId){
		const input = document.getElementById(inputId);
		const panel = document.getElementById(panelId);
		if(!input || !panel) return;
		let t;
		input.addEventListener('input', () => {
			const val = input.value.trim();
			clearTimeout(t);
			if (!val){ panel.innerHTML=''; panel.style.display='none'; return; }
			t = setTimeout(async () => {
				try{
					const r = await fetch(`/api/autocomplete?prefix=${encodeURIComponent(val)}`);
					const data = await r.json();
					panel.innerHTML = data.results.map(x => `<div class="ac-item">${x}</div>`).join('');
					panel.style.display = data.results.length ? 'block' : 'none';
					$$('.ac-item', panel).forEach(el => el.addEventListener('click', () => { input.value = el.textContent; panel.style.display='none'; }));
				}catch(e){ /* ignore */ }
			}, 150);
		});
		document.addEventListener('click', (e)=>{ if(!panel.contains(e.target) && e.target!==input){ panel.style.display='none'; } });
	}
	bindAutocomplete('q','ac');
	bindAutocomplete('title','ac-title');

	// History (store last 10 queries)
	const HIST_KEY = 'recent';
	function addRecent(type, value){
		if(!value) return;
		let arr = [];
		try{ arr = JSON.parse(localStorage.getItem(HIST_KEY) || '[]'); }catch{}
		arr.unshift({type, value, ts: Date.now()});
		arr = arr.slice(0,10);
		localStorage.setItem(HIST_KEY, JSON.stringify(arr));
	}
	const searchForm = $('#search-form');
	const similarForm = $('#similar-form');
	if (searchForm){ searchForm.addEventListener('submit', ()=> addRecent('search', $('#q').value.trim())); }
	if (similarForm){ similarForm.addEventListener('submit', ()=> addRecent('similar', $('#title').value.trim())); }
	const recentList = $('#recent-list');
	if (recentList){
		let arr=[]; try{ arr = JSON.parse(localStorage.getItem(HIST_KEY) || '[]'); }catch{}
		recentList.innerHTML = arr.map(x => `<li class="list-item"><span class="muted">${x.type}</span> ${x.value}</li>`).join('');
	}

	// Keyboard shortcuts: Enter submits, ArrowDown focuses first ac item
	function bindKeys(inputId, formSel, panelId){
		const input = document.getElementById(inputId);
		const form = $(formSel);
		const panel = document.getElementById(panelId);
		if(!input || !form || !panel) return;
		input.addEventListener('keydown', (e)=>{
			if(e.key==='Enter'){ form.requestSubmit(); }
			if(e.key==='ArrowDown'){
				const first = $('.ac-item', panel);
				if(first){ first.focus(); }
			}
		});
	}
	bindKeys('q','#search-form','ac');
	bindKeys('title','#similar-form','ac-title');

	// Copy shareable link
	const copyBtn = $('#copy-link');
	if (copyBtn){ copyBtn.addEventListener('click', async ()=>{
		try{
			await navigator.clipboard.writeText(location.href);
			copyBtn.textContent = 'Copied!';
			setTimeout(()=> copyBtn.textContent = 'Copy link', 1500);
		}catch{}
	}); }

	// Testimonials carousel
	const track = document.getElementById('t-items');
	const dots = $$('.t-dot');
	if (track && dots.length){
		let idx = 0;
		function go(i){
			idx = i;
			const step = track.children[0]?.offsetWidth + 16 || 316;
			track.style.transform = `translateX(${-step * idx}px)`;
			dots.forEach((d,j)=> d.classList.toggle('active', j===idx));
		}
		dots.forEach(d => d.addEventListener('click', ()=> go(parseInt(d.getAttribute('data-i')))));
		let timer = setInterval(()=> go((idx+1)%dots.length), 4000);
		track.addEventListener('mouseenter', ()=> clearInterval(timer));
		track.addEventListener('mouseleave', ()=> timer = setInterval(()=> go((idx+1)%dots.length), 4000));
	}
})();
