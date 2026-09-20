(() => {
  const canvas = document.querySelector('#arena'), ctx = canvas.getContext('2d'), W = 960, H = 640;
  const ui = {start: document.querySelector('#start-screen'), startButton: document.querySelector('#start'), restart: document.querySelector('#restart'), name: document.querySelector('#nickname'), room: document.querySelector('#room-code'), status: document.querySelector('#lobby-status'), health: document.querySelector('#health-fill'), healthNumber: document.querySelector('#health-number'), score: document.querySelector('#score'), kills: document.querySelector('#kills'), roomLabel: document.querySelector('#wave'), players: document.querySelector('#enemies'), timer: document.querySelector('#timer'), dash: document.querySelector('#dash-fill'), weapon: document.querySelector('#weapon-name'), ammo: document.querySelector('#ammo'), info: document.querySelector('#weapon-info')};
  const weapons = {
    rifle: {name: 'SERVICE RIFLE', rate: 120, damage: 18, speed: 700, spread: 0, color: '#56e8ff', info: 'AUTO / 18 DMG', kind: 'bullet'},
    ricochet: {name: 'REFLECTOR', rate: 380, damage: 22, speed: 560, spread: 0, color: '#78dfff', info: '2 BOUNCES / 22 DMG', kind: 'bullet', bounces: 2},
    grenade: {name: 'GRENADE', rate: 760, damage: 42, speed: 380, spread: .03, color: '#ff9f5a', info: 'BLAST / 42 DMG', kind: 'grenade', blast: 76, life: 1050},
    white_rocket: {name: 'WHITE ROCKET', rate: 900, damage: 38, speed: 440, spread: 0, color: '#f5f7ff', info: 'ROCKET / 38 DMG', kind: 'rocket', blast: 52, life: 1250},
    yellow_homing: {name: 'YELLOW SEEKER', rate: 780, damage: 30, speed: 365, spread: 0, color: '#ffe65a', info: 'LOCK-ON / 30 DMG', kind: 'homing', blast: 42, life: 1500, turn: 4.2}
  };
  const keys = new Set(), mouse = {x: W / 2, y: H / 2, down: false};
  let socket, id, room, map = 'foundry', maps = {}, players = [], self, bullets = [], particles = [], obstacles = [];
  let started = false, last = 0, startedAt = 0, lastMove = 0, lastShot = 0, dashAt = -9999, selectedMap = 'foundry';
  const url = () => `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws/arena`;
  const send = data => { if (socket?.readyState === WebSocket.OPEN) socket.send(JSON.stringify(data)); };
  const grasses = () => maps[map]?.grass || [];

  function join() {
    ui.status.textContent = '正在连接房间…'; socket = new WebSocket(url());
    socket.onopen = () => send({type: 'join', name: ui.name.value, room: ui.room.value, map: selectedMap});
    socket.onmessage = event => handle(JSON.parse(event.data));
    socket.onclose = () => { if (started) ui.status.textContent = '连接已断开。点击重新开始。'; };
    socket.onerror = () => ui.status.textContent = '无法连接联机服务器。请检查本地服务。';
  }
  function scoreTable() { const rows = document.querySelector('#score-rows'); if (rows) rows.innerHTML = players.slice().sort((a, b) => b.score - a.score).map(p => `<div class="score-row ${p.id === id ? 'me' : ''}"><span>${p.name}</span><b>${p.score}</b><span>${p.deaths} D</span></div>`).join(''); }
  function feed(text) { const box = document.querySelector('#feed'), line = document.createElement('div'); line.className = 'feed-item'; line.textContent = text; box.prepend(line); setTimeout(() => line.remove(), 4200); }
  function handle(message) {
    if (message.type === 'welcome') { id = message.id; maps = message.maps; map = message.map; room = message.room; obstacles = maps[map].obstacles.map(([x, y, w, h]) => ({x, y, w, h})); started = true; startedAt = performance.now(); ui.start.classList.add('hidden'); last = performance.now(); requestAnimationFrame(loop); }
    if (message.type === 'state') { room = message.room; map = message.map; players = message.players; self = players.find(p => p.id === id) || self; if (maps[map]) obstacles = maps[map].obstacles.map(([x, y, w, h]) => ({x, y, w, h})); scoreTable(); }
    if (message.type === 'event' && message.kind === 'shot') { const p = message.payload; bullets.push({x: p.x, y: p.y, vx: p.vx, vy: p.vy, r: p.r || 4, life: p.life || 900, color: p.color, kind: p.kind || 'bullet', bounces: p.bounces || 0, blast: p.blast || 0, damage: p.damage || 0, target: p.target, turn: p.turn || 0, remote: true}); burst(p.x, p.y, p.color, 3); }
    if (message.type === 'event' && message.kind === 'kill') feed(`${message.payload.by} eliminated ${message.payload.target}`);
    if (message.type === 'event' && message.kind === 'chat') feed(`${message.payload.name}: ${message.payload.content}`);
    if (message.type === 'error') ui.status.textContent = message.message;
  }
  function equip(weapon) { if (!self || !weapons[weapon]) return; self.weapon = weapon; send({type: 'weapon', weapon}); document.querySelectorAll('.weapon').forEach(button => button.classList.toggle('active', button.dataset.weapon === weapon)); }
  function collide(x, y, r = 16) { return x < r + 18 || x > W - r - 18 || y < r + 18 || y > H - r - 18 || obstacles.some(o => x + r > o.x && x - r < o.x + o.w && y + r > o.y && y - r < o.y + o.h); }
  function nearestTarget(from) { return players.filter(p => p.id !== id && !p.hidden).sort((a, b) => Math.hypot(a.x - from.x, a.y - from.y) - Math.hypot(b.x - from.x, b.y - from.y))[0]; }
  function fire() {
    if (!self) return; const w = weapons[self.weapon] || weapons.rifle, now = performance.now(); if (now - lastShot < w.rate) return; lastShot = now;
    const angle = Math.atan2(mouse.y - self.y, mouse.x - self.x) + (Math.random() - .5) * w.spread, damage = w.damage * (1 + (self.upgrades?.amplify || 0) * .15), target = w.kind === 'homing' ? nearestTarget(self)?.id : null;
    const bullet = {x: self.x + Math.cos(angle) * 21, y: self.y + Math.sin(angle) * 21, vx: Math.cos(angle) * w.speed, vy: Math.sin(angle) * w.speed, r: w.kind === 'grenade' ? 8 : w.kind === 'rocket' || w.kind === 'homing' ? 6 : 4, life: w.life || 900, color: w.color, damage, kind: w.kind, bounces: w.bounces || 0, blast: w.blast || 0, target, turn: w.turn || 0};
    bullets.push(bullet); send({type: 'event', kind: 'shot', payload: {...bullet}}); burst(bullet.x, bullet.y, w.color, 4);
  }
  function dash() {
    if (!self || performance.now() - dashAt < 1800) return; dashAt = performance.now(); let dx = (keys.has('d') ? 1 : 0) - (keys.has('a') ? 1 : 0), dy = (keys.has('s') ? 1 : 0) - (keys.has('w') ? 1 : 0); const a = dx || dy ? Math.atan2(dy, dx) : Math.atan2(mouse.y - self.y, mouse.x - self.x);
    for (let i = 0; i < 15; i++) { const nx = self.x + Math.cos(a) * 13, ny = self.y + Math.sin(a) * 13; if (collide(nx, ny)) break; self.x = nx; self.y = ny; particles.push({x: self.x, y: self.y, vx: (Math.random() - .5) * 30, vy: (Math.random() - .5) * 30, life: 420, color: '#956cff', r: 7}); }
    send({type: 'move', x: self.x, y: self.y});
  }
  function burst(x, y, color, count) { for (let i = 0; i < count; i++) { const a = Math.random() * 6.28, speed = 30 + Math.random() * 150; particles.push({x, y, vx: Math.cos(a) * speed, vy: Math.sin(a) * speed, life: 250 + Math.random() * 250, color, r: 2 + Math.random() * 3}); } }
  function removeBullet(bullet) { const index = bullets.indexOf(bullet); if (index >= 0) bullets.splice(index, 1); }
  function bounce(bullet) { bullet.x = bullet.lastX; bullet.y = bullet.lastY; const hitX = collide(bullet.x + bullet.vx * .022, bullet.y, bullet.r), hitY = collide(bullet.x, bullet.y + bullet.vy * .022, bullet.r); if (hitX || !hitY) bullet.vx *= -1; if (hitY || !hitX) bullet.vy *= -1; bullet.x += bullet.vx * .018; bullet.y += bullet.vy * .018; burst(bullet.x, bullet.y, bullet.color, 5); }
  function explode(bullet) {
    burst(bullet.x, bullet.y, bullet.color, bullet.kind === 'grenade' ? 20 : 13); if (bullet.remote || !bullet.blast) return;
    players.filter(target => target.id !== id && !target.hidden).forEach(target => { const distance = Math.hypot(target.x - bullet.x, target.y - bullet.y); if (distance < bullet.blast) send({type: 'damage', target: target.id, damage: Math.max(8, bullet.damage * (1 - distance / (bullet.blast * 1.15)))}); });
  }
  function steerHoming(bullet, dt) {
    const target = players.find(p => p.id === bullet.target && !p.hidden) || (bullet.remote ? null : nearestTarget(bullet)); if (!target) return; bullet.target = target.id;
    const speed = Math.hypot(bullet.vx, bullet.vy), current = Math.atan2(bullet.vy, bullet.vx), desired = Math.atan2(target.y - bullet.y, target.x - bullet.x); let turn = Math.atan2(Math.sin(desired - current), Math.cos(desired - current)); turn = Math.max(-bullet.turn * dt, Math.min(bullet.turn * dt, turn)); bullet.vx = Math.cos(current + turn) * speed; bullet.vy = Math.sin(current + turn) * speed;
  }
  function updateProjectile(bullet, dt) {
    if (bullet.kind === 'homing') steerHoming(bullet, dt); bullet.lastX = bullet.x; bullet.lastY = bullet.y; bullet.x += bullet.vx * dt; bullet.y += bullet.vy * dt; bullet.life -= dt * 1000;
    if (collide(bullet.x, bullet.y, bullet.r)) { if (bullet.bounces > 0) { bullet.bounces--; bounce(bullet); return; } explode(bullet); removeBullet(bullet); return; }
    if (bullet.life < 0) { explode(bullet); removeBullet(bullet); return; }
    if (bullet.remote) return;
    for (const target of players.filter(p => p.id !== id && !p.hidden)) { if (Math.hypot(target.x - bullet.x, target.y - bullet.y) >= 20) continue; if (bullet.blast) explode(bullet); else { send({type: 'damage', target: target.id, damage: bullet.damage}); burst(bullet.x, bullet.y, bullet.color, 6); } removeBullet(bullet); break; }
  }
  function update(dt) {
    if (!self) return; let dx = (keys.has('d') ? 1 : 0) - (keys.has('a') ? 1 : 0), dy = (keys.has('s') ? 1 : 0) - (keys.has('w') ? 1 : 0), speed = (190 + (self.upgrades?.velocity || 0) * 30) * dt;
    if (dx || dy) { const length = Math.hypot(dx, dy); dx = dx / length * speed; dy = dy / length * speed; if (!collide(self.x + dx, self.y)) self.x += dx; if (!collide(self.x, self.y + dy)) self.y += dy; }
    if (mouse.down) fire(); for (const bullet of [...bullets]) updateProjectile(bullet, dt); for (const particle of particles) { particle.x += particle.vx * dt; particle.y += particle.vy * dt; particle.life -= dt * 1000; } particles = particles.filter(p => p.life > 0); if (performance.now() - lastMove > 50) { send({type: 'move', x: self.x, y: self.y}); lastMove = performance.now(); } sync();
  }
  function grid() { ctx.strokeStyle = '#17223a'; for (let x = 0; x < W; x += 40) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke(); } for (let y = 0; y < H; y += 40) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke(); } ctx.strokeStyle = maps[map]?.accent || '#33425f'; ctx.strokeRect(18, 18, W - 36, H - 36); }
  function drawGrass() { for (const [x, y, w, h] of grasses()) { ctx.fillStyle = '#123f30'; ctx.fillRect(x, y, w, h); ctx.strokeStyle = '#2b7a51'; ctx.strokeRect(x, y, w, h); ctx.strokeStyle = '#46a86a'; for (let gx = x + 7; gx < x + w; gx += 9) for (let gy = y + 8; gy < y + h; gy += 12) { ctx.beginPath(); ctx.moveTo(gx, gy + 5); ctx.lineTo(gx - 2, gy - 4); ctx.moveTo(gx, gy + 5); ctx.lineTo(gx + 3, gy - 3); ctx.stroke(); } } }
  function person(p, local = false) {
    if (p.hidden && !local) return; if (p.shielded) { ctx.strokeStyle = '#a58cff'; ctx.shadowBlur = 16; ctx.shadowColor = '#a58cff'; ctx.beginPath(); ctx.arc(p.x, p.y, 27, 0, 6.28); ctx.stroke(); ctx.shadowBlur = 0; }
    const a = local ? Math.atan2(mouse.y - p.y, mouse.x - p.x) : 0; ctx.save(); ctx.translate(p.x, p.y); ctx.rotate(a); ctx.fillStyle = local ? '#d7fbff' : p.hue; ctx.shadowBlur = local ? 18 : 8; ctx.shadowColor = ctx.fillStyle; ctx.beginPath(); ctx.moveTo(20, 0); ctx.lineTo(-11, -12); ctx.lineTo(-6, 0); ctx.lineTo(-11, 12); ctx.closePath(); ctx.fill(); ctx.restore(); ctx.shadowBlur = 0; ctx.fillStyle = '#202b42'; ctx.fillRect(p.x - 18, p.y - 29, 36, 3); ctx.fillStyle = p.hue; ctx.fillRect(p.x - 18, p.y - 29, 36 * Math.max(0, p.hp) / 100, 3); ctx.fillStyle = '#d6e5ff'; ctx.font = '10px DM Mono'; ctx.textAlign = 'center'; ctx.fillText(p.name, p.x, p.y + 31);
  }
  function drawProjectile(bullet) { ctx.save(); ctx.fillStyle = bullet.color; ctx.shadowBlur = bullet.kind === 'homing' ? 20 : 10; ctx.shadowColor = bullet.color; if (bullet.kind === 'grenade') { ctx.beginPath(); ctx.arc(bullet.x, bullet.y, bullet.r, 0, 6.28); ctx.fill(); ctx.strokeStyle = '#fff0c0'; ctx.stroke(); } else if (bullet.kind === 'rocket' || bullet.kind === 'homing') { const a = Math.atan2(bullet.vy, bullet.vx); ctx.translate(bullet.x, bullet.y); ctx.rotate(a); ctx.fillRect(-8, -3, 16, 6); ctx.fillStyle = bullet.kind === 'homing' ? '#ff9e42' : '#bcd1ff'; ctx.fillRect(-13, -2, 7, 4); } else { ctx.beginPath(); ctx.arc(bullet.x, bullet.y, bullet.r, 0, 6.28); ctx.fill(); } ctx.restore(); ctx.shadowBlur = 0; }
  function draw() { ctx.fillStyle = '#080d18'; ctx.fillRect(0, 0, W, H); grid(); drawGrass(); for (const o of obstacles) { ctx.fillStyle = '#101a2d'; ctx.fillRect(o.x, o.y, o.w, o.h); ctx.strokeStyle = '#33425b'; ctx.strokeRect(o.x, o.y, o.w, o.h); ctx.fillStyle = '#1a2944'; ctx.fillRect(o.x + 7, o.y + 7, o.w - 14, 3); } for (const bullet of bullets) drawProjectile(bullet); for (const p of players) person(p, p.id === id); for (const p of particles) { ctx.globalAlpha = Math.max(0, p.life / 500); ctx.fillStyle = p.color; ctx.fillRect(p.x, p.y, p.r, p.r); ctx.globalAlpha = 1; } }
  function sync() { if (!self) return; ui.health.style.width = Math.max(0, self.hp) + '%'; ui.healthNumber.textContent = `${Math.max(0, self.hp)} / 100`; ui.score.textContent = String(self.score || 0).padStart(4, '0'); ui.kills.textContent = Math.floor((self.score || 0) / 100); ui.roomLabel.textContent = room || '—'; ui.players.textContent = `${players.length} players · ${maps[map]?.name || map}`; const weapon = weapons[self.weapon] || weapons.rifle; ui.weapon.textContent = weapon.name; ui.ammo.textContent = weapon.kind === 'bullet' ? (weapon.bounces ? '02' : '∞') : '01'; ui.info.textContent = weapon.info; ui.dash.style.width = Math.min(100, (performance.now() - dashAt) / 18) + '%'; const seconds = Math.floor((performance.now() - startedAt) / 1000); ui.timer.textContent = `${String(Math.floor(seconds / 60)).padStart(2, '0')}:${String(seconds % 60).padStart(2, '0')}`; }
  function loop(now) { if (!started) return; const dt = Math.min(.035, (now - last) / 1000); last = now; update(dt); draw(); requestAnimationFrame(loop); }
  canvas.addEventListener('mousemove', event => { const box = canvas.getBoundingClientRect(); mouse.x = (event.clientX - box.left) * W / box.width; mouse.y = (event.clientY - box.top) * H / box.height; }); canvas.addEventListener('mousedown', event => { if (event.button === 0) mouse.down = true; }); window.addEventListener('mouseup', () => mouse.down = false);
  window.addEventListener('keydown', event => { const key = event.key.toLowerCase(); if (['w', 'a', 's', 'd', ' ', '1', '2', '3', '4', '5', 'q', 'e', 'r', 'v', 'x', 'c'].includes(key)) event.preventDefault(); keys.add(key); if (key === ' ') dash(); if ('12345'.includes(key)) equip(['rifle', 'ricochet', 'grenade', 'white_rocket', 'yellow_homing'][+key - 1]); if (key === 'q') send({type: 'ability', ability: 'shield'}); if (key === 'e') send({type: 'ability', ability: 'repair'}); if ('vxc'.includes(key)) send({type: 'upgrade', upgrade: {v: 'vitality', x: 'velocity', c: 'amplify'}[key]}); if (key === 'r') location.reload(); }); window.addEventListener('keyup', event => keys.delete(event.key.toLowerCase()));
  document.querySelectorAll('.weapon').forEach(button => button.onclick = () => equip(button.dataset.weapon)); document.querySelectorAll('[data-upgrade]').forEach(button => button.onclick = () => send({type: 'upgrade', upgrade: button.dataset.upgrade})); document.querySelectorAll('[data-map]').forEach(button => button.onclick = () => { selectedMap = button.dataset.map; document.querySelectorAll('[data-map]').forEach(item => item.classList.toggle('active', item === button)); }); ui.startButton.onclick = join; ui.restart.onclick = () => location.reload(); draw();
  const chat = document.querySelector('#chat'), chatInput = document.querySelector('#chat-input'), scoreboard = document.querySelector('#scoreboard'); chat.addEventListener('submit', event => { event.preventDefault(); const content = chatInput.value.trim(); if (content) send({type: 'chat', content}); chatInput.value = ''; chat.classList.add('hidden'); canvas.focus(); }); window.addEventListener('keydown', event => { if (event.key === 'Tab' && started) { event.preventDefault(); scoreboard.classList.remove('hidden'); } if (event.key === 'Enter' && started && document.activeElement !== chatInput) { event.preventDefault(); chat.classList.remove('hidden'); chatInput.focus(); } }); window.addEventListener('keyup', event => { if (event.key === 'Tab') scoreboard.classList.add('hidden'); });
})();
