'use strict';
import {
  copy
} from './i18n.js';
const $ = s => document.querySelector(s);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({
  '&': '&amp;',
  '<': '&lt;',
  '>': '&gt;',
  '"': '&quot;',
  "'": '&#39;'
} [c]));
const icons = {
  grid: '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
  book: '<path d="M3 4h7l2 2 2-2h7v15h-7l-2 2-2-2H3zM12 6v15"/>',
  chart: '<path d="M4 3v18h17M8 16v-4m5 4V8m5 8V5"/>',
  upload: '<path d="M12 16V3m-5 5 5-5 5 5M4 15v6h16v-6"/>',
  file: '<path d="M14 2H5v20h14V7zM14 2v6h5M8 12h8m-8 4h6"/>',
  moon: '<path d="M20 14A9 9 0 0 1 10 3a9 9 0 1 0 10 11z"/>',
  logout: '<path d="M9 4H3v16h6m6-13 5 5-5 5m-7-5h12"/>',
  cards: '<rect x="6" y="6" width="15" height="15" rx="2"/><path d="M17 3H3v14m7-6h7m-7 5h4"/>',
  check: '<path d="m5 12 4 4L20 5"/>',
  plus: '<path d="M12 5v14M5 12h14"/>'
};
const icon = name => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${icons[name]||icons.book}</svg>`;

let lang = localStorage.getItem('studylens-lang') || 'en',
  theme = localStorage.getItem('studylens-theme') || 'light';
if (!copy[lang]) lang = 'en';
let publicDemo = false;
let user = null,
  docs = [],
  progress = {},
  page = 'dashboard',
  doc = null,
  tab = 'summary',
  authMode = 'login',
  cardIndex = 0,
  revealed = false,
  quiz = null,
  result = null,
  answers = [],
  chat = null,
  deleting = false,
  busy = false;
const t = key => copy[lang][key] || key;
const title = s => s.replace(/\.(txt|md|pdf|pptx)$/i, '').replace(/[-_]/g, ' ');
const brand = () => '<div class="brand"><img src="/assets/icon.svg" alt=""><span>Study<span>Lens</span></span></div>';
const art = () => '<div class="hero-art" aria-hidden="true"><div class="orb"></div><div class="paper"><i></i><i></i><i></i><i></i></div><span class="spark">✦</span></div>';
const date = d => new Date(d).toLocaleDateString(lang === 'ar' ? 'ar-SA' : 'en-GB', {
  month: 'short',
  day: 'numeric',
  year: 'numeric'
});
const controls = () => `<button class="icon-btn" data-action="lang" aria-label="${t('lang')}">${t('lang')}</button><button class="icon-btn" data-action="theme" aria-label="${t('theme')}">${icon('moon')}</button>`;

function preferences() {
  document.documentElement.lang = lang;
  document.documentElement.dir = lang === 'ar' ? 'rtl' : 'ltr';
  document.documentElement.dataset.theme = theme;
  localStorage.setItem('studylens-lang', lang);
  localStorage.setItem('studylens-theme', theme);
}

function toast(message) {
  $('#toast').textContent = message;
  $('#toast').classList.add('show');
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => $('#toast').classList.remove('show'), 4200);
}
async function api(path, options = {}) {
  const response = await fetch('/api' + path, {
    ...options,
    headers: options.body instanceof FormData ? {} : {
      'Content-Type': 'application/json',
      ...options.headers
    }
  });
  if (response.status === 204) return null;
  const body = await response.json();
  if (!response.ok) {
    if (response.status === 401 && user) {
      user = null;
      render();
    }
    throw new Error(typeof body.detail === 'string' ? body.detail : body.detail?.map(e => e.msg).join(' · ') || t('error'));
  }
  return body;
}
async function refresh() {
  [docs, progress] = await Promise.all([api('/documents'), api('/progress')]);
}

function auth() {
  return `<main class="auth-layout"><section class="auth-story">${brand()}<h1>${t('authTitle').replace('\n','<br>')}</h1><p>${t('authText')}</p>${art()}<small>${t('privacy')}</small></section><section class="auth-main"><div class="auth-box"><div class="tools">${controls()}</div>${brand()}<h2>${t(publicDemo?'demoTitle':authMode==='login'?'welcome':'create')}</h2><p>${t('authSub')}</p><section class="demo-entry"><span class="demo-label">${t('demoBadge')}</span><button class="btn" type="button" data-action="demo">${icon('plus')}${t('enterDemo')}</button><p>${t('demoHint')}</p></section>${publicDemo?'':`<div class="auth-divider">${t('orAccount')}</div><form id="auth-form">${authMode==='register'?`<div class="field"><label for="name">${t('name')}</label><input class="input" id="name" name="name" required maxlength="80" autocomplete="name"></div>`:''}<div class="field"><label for="email">${t('email')}</label><input class="input" id="email" name="email" type="email" required autocomplete="email" dir="ltr"></div><div class="field"><label for="password">${t('password')}</label><input class="input" id="password" name="password" type="password" minlength="8" maxlength="128" placeholder="${t('passwordHint')}" required autocomplete="${authMode==='login'?'current-password':'new-password'}"></div><p class="error" id="auth-error" role="alert"></p><button class="btn" type="submit">${t(authMode==='login'?'login':'register')}</button></form><div class="auth-switch">${t(authMode==='login'?'newHere':'haveAccount')} <button class="text-btn" data-action="auth-switch">${t(authMode==='login'?'register':'login')}</button></div>`}</div></section></main>`;
}

function stats() {
  return `<div class="stats">${[['documents','docHint','book'],['quizzes','quizHint','check'],['average','avgHint','chart'],['reviews','reviewHint','cards']].map(([key,hint,ic])=>`<div class="stat"><div class="stat-top">${t(key)}<span class="stat-icon">${icon(ic)}</span></div><strong>${progress[key]||0}${key==='average'?'%':''}</strong><small>${t(hint)}</small></div>`).join('')}</div>`;
}

function documentItem(d) {
  return `<button class="document" data-doc="${d.id}"><span class="file-icon">${icon('file')}</span><span class="document-info"><h3 dir="auto">${esc(title(d.title))}</h3><small>${d.pages} ${t('pages')} &nbsp; · &nbsp; ${date(d.created_at)}</small></span><span class="badge">${t('ready')}</span><span class="arrow">${lang==='ar'?'‹':'›'}</span></button>`;
}

function drop() {
  return `<div class="upload-zone" role="button" tabindex="0" data-action="upload" aria-label="${t('browse')}">${icon('upload')}<strong>${t('drop')}</strong><small>${t('dropHint')}</small></div>`;
}

function overview() {
  return `<div class="heading"><div><h1>${t('greeting')}</h1><p>${t('greetSub')}</p></div><button class="btn" data-action="upload">${icon('plus')}${t('upload')}</button></div><section class="hero"><div><div class="kicker">${t('heroLabel')}</div><h2>${t('heroTitle').replace('\n','<br>')}</h2><p>${t('heroText')}</p><button class="btn" data-action="samples">${t('sample')} <span aria-hidden="true">${lang==='ar'?'←':'→'}</span></button></div>${art()}</section>${stats()}<div class="workspace-grid"><section><div class="section-head"><h2>${t('recent')}</h2><button class="text-btn" data-page="library">${t('viewAll')} ${lang==='ar'?'←':'→'}</button></div><div class="document-list">${docs.length?docs.slice(0,3).map(documentItem).join(''):`<div class="empty">${t('empty')}</div>`}</div>${drop()}</section><aside class="guide"><div class="panel"><h3>${t('guide')}</h3><div class="steps">${[1,2,3].map(i=>`<div class="step"><span class="step-number">${i}</span><div><b>${t('step'+i)}</b><span class="muted">${t('step'+i+'text')}</span></div></div>`).join('')}</div></div><div class="tip"><strong>✧ &nbsp;${t('tip')}</strong>${t('tipText')}</div></aside></div>`;
}

function library() {
  return `<div class="heading"><div><h1>${t('library')}</h1><p>${t('librarySub')}</p></div><button class="btn" data-action="upload">${icon('plus')}${t('upload')}</button></div><div class="section-head"><small>${docs.length} ${t('documents')}</small><input class="input search" id="search" placeholder="${t('search')}" aria-label="${t('search')}"></div><div class="library-grid" id="library-list">${docs.map(documentItem).join('')}</div>${!docs.length?`<div class="empty">${t('empty')}<br><button class="btn ghost" data-action="samples">${t('sample')}</button></div>`:''}${drop()}`;
}

function progressPage() {
  return `<div class="heading"><div><h1>${t('progress')}</h1><p>${t('progressSub')}</p></div></div>${stats()}<section class="panel"><h3>${t('history')}</h3>${progress.history?.length?`<table class="table"><thead><tr><th>${t('documents')}</th><th>${t('date')}</th><th>${t('score')}</th></tr></thead><tbody>${progress.history.map(h=>`<tr><td dir="auto">${esc(title(h.title))}</td><td>${date(h.created_at)}</td><td><strong>${h.score}%</strong></td></tr>`).join('')}</tbody></table>`:`<div class="empty">${t('noHistory')}</div>`}<p class="muted">${t('scoreNote')}</p></section>`;
}

function sourceBlock(s) {
  return `<div class="source"><div dir="auto" class="source-text">${esc(s.text)}</div><small>${t('page')} ${s.page} · #${s.chunk_id||s.id}</small></div>`;
}

function study() {
  return `<div class="heading"><div><button class="text-btn" data-page="library">${lang==='ar'?'→':'←'} ${t('back')}</button><h1 dir="auto">${esc(title(doc.title))}</h1><p>${doc.pages} ${t('pages')} · ${date(doc.created_at)}</p></div><button class="btn secondary" data-action="delete">${t('delete')}</button></div>${deleting?`<div class="confirm"><span>${t('confirmDelete')}</span><button class="btn danger" data-action="confirm-delete">${t('delete')}</button><button class="btn secondary" data-action="cancel-delete">${t('cancel')}</button></div>`:''}<div class="notice">${t('engine')}</div><div class="tabs" role="tablist">${['summary','cards','quiz','ask','source'].map(k=>`<button role="tab" aria-selected="${tab===k}" class="${tab===k?'active':''}" data-tab="${k}">${t(k)}</button>`).join('')}</div><div class="study-body" role="tabpanel">${studyBody()}</div>`;
}

function studyBody() {
  if (tab === 'summary') return `<p class="muted">${t('summaryIntro')}</p>${doc.summary.map(sourceBlock).join('')}`;
  if (tab === 'source') return doc.source.map(sourceBlock).join('');
  if (tab === 'cards') {
    const c = doc.cards[cardIndex];
    return c ? `<div class="section-head"><small>${t('card')} ${cardIndex+1} / ${doc.cards.length}</small><small>${t('page')} ${c.source.page}</small></div><button class="card" data-action="flip"><small>${t(revealed?'reviewSource':'flip')}</small><span dir="auto" class="${revealed?'answer':''}">${esc(revealed?c.back:c.front)}</span>${revealed?`<small dir="auto">${esc(c.source.text)}</small>`:''}</button><div class="card-actions"><button class="btn secondary" data-review="again">${t('again')}</button><button class="btn" data-review="known">${icon('check')}${t('known')}</button></div>` : `<div class="empty">${t('noCards')}</div>`;
  }
  if (tab === 'quiz') {
    if (!quiz) return `<div class="panel"><h3>${t('quiz')}</h3><p class="muted">${t('quizIntro')}</p><br><button class="btn" data-action="start-quiz">${t('startQuiz')}</button></div>`;
    if (result) return `<div class="panel"><div class="score">${result.score}%</div><h3>${t('quizResult')}</h3><button class="btn" data-action="start-quiz">${t('retake')}</button></div>${result.questions.map((q,i)=>`<div class="quiz-question"><p dir="auto">${i+1}. ${esc(q.prompt)}</p><div class="options">${q.options.map((o,j)=>`<div class="option ${j===q.correct?'correct':j===result.answers[i]?'wrong':''}">${j===q.correct?'✓ ':j===result.answers[i]?'× ':''}${esc(o)}</div>`).join('')}</div>${sourceBlock(q.source)}</div>`).join('')}`;
    return `<form id="quiz-form">${quiz.questions.map((q,i)=>`<fieldset class="quiz-question"><legend>${i+1} / ${quiz.questions.length}</legend><p dir="auto">${esc(q.prompt)}</p><div class="options">${q.options.map((o,j)=>`<label class="option" dir="auto"><input type="radio" name="q${i}" value="${j}" data-question="${i}" ${answers[i]===j?'checked':''} required>${esc(o)}</label>`).join('')}</div></fieldset>`).join('')}<button class="btn" type="submit">${t('submit')}</button></form>`;
  }
  return `<p class="muted">${t('askIntro')}</p><form class="ask-form" id="ask-form"><input class="input" name="question" aria-label="${t('question')}" placeholder="${t('askPlaceholder')}" minlength="3" maxlength="500" required><button class="btn" type="submit">${t('askButton')}</button></form>${chat?`<div class="notice" dir="auto">${esc(chat.question)}</div><h3>${t(chat.found?'citations':'noAnswer')}</h3>${chat.sources.map(sourceBlock).join('')}`:''}`;
}

function render() {
  preferences();
  if (!user) {
    $('#app').innerHTML = auth();
    return;
  }
  $('#app').innerHTML = `<div class="shell"><aside class="sidebar">${brand()}<div class="eyebrow">${t('workspace')}</div><nav class="nav">${[['dashboard','grid'],['library','book'],['progress','chart']].map(([k,i])=>`<button class="${(page===k||(page==='study'&&k==='library'))?'active':''}" data-page="${k}">${icon(i)}${t(k)}</button>`).join('')}</nav><div class="sidebar-note"><strong>◉ &nbsp;${t(publicDemo?'sharedDemo':'local')}</strong>${t(publicDemo?'sharedNote':'localNote')}</div><div class="profile"><div class="avatar">${esc(user.name.slice(0,1).toUpperCase())}</div><div><strong>${esc(user.is_demo?t('demoName'):user.name)}</strong><small>${t(user?.is_demo?'demoBadge':'student')}</small></div><button class="icon-btn" data-action="logout" aria-label="${t('logout')}">${icon('logout')}</button></div></aside><main class="main"><header class="topbar"><span class="muted">${t(user?.is_demo?'demoBadge':'student')} &nbsp; / &nbsp; ${t(page==='study'?'library':page)}</span><div class="tools"><span class="status"><span class="dot"></span>${t(publicDemo?'sharedDemo':'local')}</span>${controls()}<button class="icon-btn" data-action="logout" aria-label="${t('logout')}">${icon('logout')}</button></div></header><div class="content">${user.is_demo?`<div class="notice demo-notice">${t("sessionHint")}</div>`:""}${page==='dashboard'?overview():page==='library'?library():page==='progress'?progressPage():study()}<footer class="footer"><span>${t(publicDemo?'sharedFooter':'footer')}</span><a href="/docs" target="_blank" rel="noopener">${t('api')} ↗</a></footer></div></main></div><input type="file" id="file-input" accept=".pdf,.pptx,.txt,.md" hidden>`;
}
async function upload(file) {
  if (!file) return;
  if (file.size > 10 * 1024 * 1024) throw new Error(t('dropHint'));
  const data = new FormData();
  data.append('file', file);
  toast(t('working'));
  const d = await api('/documents', {
    method: 'POST',
    body: data
  });
  await refresh();
  await openDoc(d.id);
  toast(t('uploaded'));
}
async function openDoc(id) {
  doc = await api('/documents/' + id);
  page = 'study';
  tab = 'summary';
  cardIndex = 0;
  revealed = false;
  quiz = null;
  result = null;
  answers = [];
  chat = null;
  deleting = false;
  render();
}
async function run(action, el) {
  if (busy) return;
  busy = true;
  if (el?.tagName === 'BUTTON') el.disabled = true;
  try {
    await action();
  } catch (e) {
    toast(e.message || t('error'));
  } finally {
    busy = false;
    if (el) el.disabled = false;
  }
}
document.addEventListener('click', event => {
  const el = event.target.closest('button,[data-action]');
  if (!el) return;
  const action = el.dataset.action;
  if (action === 'lang') {
    lang = lang === 'en' ? 'ar' : 'en';
    render();
    return;
  }
  if (action === 'theme') {
    theme = theme === 'light' ? 'dark' : 'light';
    preferences();
    return;
  }
  if (action === 'auth-switch') {
    authMode = authMode === 'login' ? 'register' : 'login';
    render();
    return;
  }
  if (busy) return;
  if (action === 'demo') {
    run(async () => {
      user = await api('/auth/demo', {
        method: 'POST'
      });
      page = 'dashboard';
      await refresh();
      render();
      toast(t('demoReady'));
    }, el);
    return;
  }
  if (el.dataset.page) {
    page = el.dataset.page;
    deleting = false;
    render();
    return;
  }
  if (el.dataset.tab) {
    tab = el.dataset.tab;
    render();
    return;
  }
  if (el.dataset.doc) {
    run(() => openDoc(el.dataset.doc), el);
    return;
  }
  if (el.dataset.review) {
    run(async () => {
      await api(`/documents/${doc.id}/reviews`, {
        method: 'POST',
        body: JSON.stringify({
          card_index: cardIndex,
          rating: el.dataset.review
        })
      });
      cardIndex = (cardIndex + 1) % doc.cards.length;
      revealed = false;
      await refresh();
      render();
      toast(t('reviewDone'));
    }, el);
    return;
  }
  if (action === 'upload') {
    $('#file-input').click();
    return;
  }
  if (action === 'flip') {
    revealed = !revealed;
    render();
    return;
  }
  if (action === 'delete' || action === 'cancel-delete') {
    deleting = action === 'delete';
    render();
    return;
  }
  if (!action) return;
  run(async () => {
    if (action === 'logout') {
      await api('/auth/logout', {
        method: 'POST'
      });
      user = null;
      docs = [];
      progress = {};
      doc = null;
      render();
    }
    if (action === 'samples') {
      await api('/documents/samples', {
        method: 'POST'
      });
      await refresh();
      render();
      toast(t('sampleAdded'));
    }
    if (action === 'confirm-delete') {
      await api('/documents/' + doc.id, {
        method: 'DELETE'
      });
      await refresh();
      page = 'library';
      doc = null;
      render();
      toast(t('deleted'));
    }
    if (action === 'start-quiz') {
      quiz = await api(`/documents/${doc.id}/quizzes`, {
        method: 'POST'
      });
      result = null;
      answers = [];
      render();
    }
  }, el);
});
document.addEventListener('submit', event => {
  event.preventDefault();
  const form = event.target;
  run(async () => {
    if (form.id === 'auth-form') {
      try {
        const data = Object.fromEntries(new FormData(form));
        user = await api('/auth/' + authMode, {
          method: 'POST',
          body: JSON.stringify(data)
        });
        page = 'dashboard';
        await refresh();
        render();
      } catch (e) {
        const error = $('#auth-error');
        if (error) error.textContent = e.message;
        else throw e;
      }
    }
    if (form.id === 'quiz-form') {
      const selected = quiz.questions.map((_, i) => Number(new FormData(form).get('q' + i)));
      result = await api('/quizzes/' + quiz.id + '/submit', {
        method: 'POST',
        body: JSON.stringify({
          answers: selected
        })
      });
      await refresh();
      render();
    }
    if (form.id === 'ask-form') {
      const question = new FormData(form).get('question');
      chat = {
        ...await api(`/documents/${doc.id}/ask`, {
          method: 'POST',
          body: JSON.stringify({
            question
          })
        }),
        question
      };
      render();
    }
  }, form.querySelector('button[type=submit]'));
});
document.addEventListener('change', event => {
  if (event.target.id === 'file-input') run(() => upload(event.target.files[0]));
  if (event.target.dataset.question !== undefined) answers[Number(event.target.dataset.question)] = Number(event.target.value);
});
document.addEventListener('input', event => {
  if (event.target.id === 'search') {
    const found = docs.filter(d => d.title.toLowerCase().includes(event.target.value.toLowerCase()));
    $('#library-list').innerHTML = found.length ? found.map(documentItem).join('') : `<div class="empty">${t('noResults')}</div>`;
  }
});
document.addEventListener('keydown', event => {
  if (event.target.classList.contains('upload-zone') && ['Enter', ' '].includes(event.key)) {
    event.preventDefault();
    $('#file-input').click();
  }
});
for (const type of ['dragover', 'dragleave', 'drop']) document.addEventListener(type, event => {
  const zone = event.target.closest('.upload-zone');
  if (!zone) return;
  event.preventDefault();
  zone.classList.toggle('drag', type === 'dragover');
  if (type === 'drop') run(() => upload(event.dataTransfer.files[0]));
});
preferences();
$('#app').innerHTML = '<div class="loading">StudyLens…</div>';
(async () => {
  try {
    publicDemo = (await api('/config')).public_demo_only;
    user = await api('/auth/me');
    await refresh();
  } catch (e) {
    user = null;
  }
  render();
})();
