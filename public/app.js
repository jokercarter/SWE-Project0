(() => {
  const workbenchLinks=document.createElement('script');
  workbenchLinks.src='/workbench-links.js';document.head.append(workbenchLinks);
  const translations = {
    en: {navProjects:'Projects', navLearning:'Learning', navAbout:'About', toggle:'中文', run:'Run ▶', running:'Running locally…', codeHint:'Click Run to execute this example with local Python.'},
    zh: {navProjects:'项目', navLearning:'学习计划', navAbout:'关于', toggle:'EN', run:'运行 ▶', running:'正在本地运行…', codeHint:'点击“运行”，使用本机 Python 执行这个示例。'}
  };
  const languageKey = 'jokercarter.language';
  let language = localStorage.getItem(languageKey) || ((navigator.language || '').toLowerCase().startsWith('zh') ? 'zh' : 'en');
  function applyLanguage() {
    const t = translations[language];
    document.documentElement.lang = language === 'zh' ? 'zh-CN' : 'en';
    document.querySelectorAll('[data-i18n]').forEach(el => { if(t[el.dataset.i18n]) el.textContent=t[el.dataset.i18n]; });
    document.querySelectorAll('[data-language-toggle]').forEach(el => { el.textContent=t.toggle; el.setAttribute('aria-label', language==='zh'?'Switch to English':'切换为中文'); });
    document.querySelectorAll('.run-cell').forEach(el => { if(!el.disabled) el.textContent=t.run; });
    document.querySelectorAll('.code-output').forEach(el => { if(!el.dataset.ran) el.textContent=t.codeHint; });
    document.body.dataset.language=language;
    const pairs = window.sitePairs || [];
    const map = new Map(pairs.map(pair => language === 'zh' ? pair : [pair[1], pair[0]]));
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    const nodes=[]; while(walker.nextNode()) nodes.push(walker.currentNode);
    nodes.forEach(node => { if(node.parentElement.closest('script,style,pre,code')) return; const value=node.nodeValue.trim(); if(!value || !map.has(value)) return; node.nodeValue=node.nodeValue.replace(value,map.get(value)); });
  }
  document.querySelectorAll('[data-language-toggle]').forEach(button => button.addEventListener('click', () => { language=language==='zh'?'en':'zh'; localStorage.setItem(languageKey, language); applyLanguage(); }));
  applyLanguage();
  async function runNotebookCell(button) {
      const cell = button.closest('.notebook-cell');
      const output = cell.querySelector('.code-output');
      button.disabled = true; output.dataset.ran='1'; output.textContent = translations[language].running;
      try {
        const response = await fetch('/api/run-python', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({week:button.dataset.week, cell:Number(button.dataset.cell)})});
        const result = await response.json();
        output.textContent = (result.stdout || '') + (result.stderr ? `\n${result.stderr}` : '') || 'Process finished with no output.';
        output.classList.toggle('run-error', !result.ok);
      } catch (error) { output.textContent = `无法连接本地运行服务：${error.message}`; output.classList.add('run-error'); }
      button.disabled = false; applyLanguage();
  }
  document.querySelectorAll('.run-cell').forEach(button => button.addEventListener('click', () => runNotebookCell(button)));
  document.querySelectorAll('.run-all').forEach(button => button.addEventListener('click', async () => {
    button.disabled=true;
    for (const cellButton of button.closest('.notebook').querySelectorAll('.run-cell')) await runNotebookCell(cellButton);
    button.disabled=false;
  }));
  const storageKey = 'jokercarter.learning.progress.v1';
  const saved = JSON.parse(localStorage.getItem(storageKey) || '{}');
  document.querySelectorAll('.chapter-checklist input[type="checkbox"]').forEach(input => {
    const key = `${input.dataset.week}-${input.dataset.chapter}`;
    input.checked = Boolean(saved[key]);
    input.addEventListener('change', () => {
      saved[key] = input.checked;
      localStorage.setItem(storageKey, JSON.stringify(saved));
      const box = input.closest('.chapter-checklist');
      const all = [...box.querySelectorAll('input')];
      box.classList.toggle('complete', all.every(item => item.checked));
    });
    input.dispatchEvent(new Event('change'));
  });
  const grid = document.querySelector('.path-grid');
  if (!grid) return;
  const rows = 8, cols = 12, start = 25, end = 70;
  const initialWalls = [8,20,32,44,56,50,51,52,53,54,17,29,41,77,78,79];
  let walls = new Set(initialWalls), running = false;
  const status = document.querySelector('#path-status');
  const run = document.querySelector('.run-button');
  const reset = document.querySelector('.reset-button');
  const cells = [];
  function clean() { cells.forEach(c => c.classList.remove('visited','path')); }
  function syncCell(i) {
    const c = cells[i];
    c.classList.toggle('wall', walls.has(i));
    c.setAttribute('aria-label', `Row ${Math.floor(i/cols)+1}, column ${i%cols+1}: ${i===start?'start':i===end?'finish':walls.has(i)?'wall, select to remove':'open, select to add wall'}`);
    if(i!==start && i!==end) c.setAttribute('aria-pressed', String(walls.has(i)));
  }
  for(let i=0;i<rows*cols;i++) {
    const cell=document.createElement('button');cell.type='button';cell.className='cell';
    if(i===start || i===end){cell.classList.add(i===start?'start':'end');cell.textContent=i===start?'S':'E';cell.disabled=true;}
    cell.addEventListener('click',()=>{if(running)return;clean();walls.has(i)?walls.delete(i):walls.add(i);syncCell(i);status.textContent='Your grid. Your way through.';});
    cells.push(cell);grid.append(cell);syncCell(i);
  }
  reset.addEventListener('click',()=>{if(running)return;walls=new Set(initialWalls);clean();cells.forEach((_,i)=>syncCell(i));status.textContent='Every good idea starts with a path.';});
  const pause = ms => new Promise(resolve=>setTimeout(resolve,ms));
  run.addEventListener('click',async()=>{
    if(running)return;running=true;clean();run.disabled=true;reset.disabled=true;
    cells.forEach(c=>c.disabled=true);status.textContent='Exploring, one neighbor at a time…';
    const queue=[start], parents=new Map([[start,null]]), visited=[];
    for(let head=0;head<queue.length;head++){
      const current=queue[head];visited.push(current);if(current===end)break;
      const r=Math.floor(current/cols),c=current%cols;
      for(const [nr,nc] of [[r-1,c],[r,c+1],[r+1,c],[r,c-1]]){
        if(nr<0||nr>=rows||nc<0||nc>=cols)continue;
        const next=nr*cols+nc;if(walls.has(next)||parents.has(next))continue;
        parents.set(next,current);queue.push(next);
      }
    }
    const reduced=window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    for(const i of visited){if(!reduced)await pause(14);if(i!==start&&i!==end)cells[i].classList.add('visited');}
    if(parents.has(end)){
      const path=[];for(let i=end;i!==null;i=parents.get(i))path.unshift(i);
      for(const i of path){if(!reduced)await pause(30);cells[i].classList.add('path');}
      status.textContent=`A way forward: ${path.length-1} steps. ${visited.length} cells explored.`;
    }else{status.textContent='No path yet. Remove a wall and try again.';}
    running=false;run.disabled=false;reset.disabled=false;cells.forEach((c,i)=>c.disabled=i===start||i===end);
  });
})();
