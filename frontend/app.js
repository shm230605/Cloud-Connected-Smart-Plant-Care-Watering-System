const deviceId = 'PLANT-001';
let activePlantId = deviceId;
const plantProfiles = {
	'ALOE-002': { name: 'Aloe Vera', type: 'ALOE VERA', location: 'Bedroom shelf', soil: 68, temperature: 23.1, humidity: 48, light: 61, threshold: 20 },
	'BASIL-003': { name: 'Kitchen Basil', type: 'BASIL', location: 'Kitchen window', soil: 74, temperature: 24.6, humidity: 57, light: 83, threshold: 35 },
	'MONSTERA-004': { name: 'Monstera', type: 'MONSTERA', location: 'Living room', soil: 59, temperature: 22.8, humidity: 68, light: 48, threshold: 30 }
};
const $ = (id) => document.getElementById(id);
let history = [];

const authScreen = $('auth-screen');
const appShell = $('app-shell');
const authForm = $('auth-form');
let authMode = 'signin';

function showWorkspace() {
	authScreen.style.display = 'none';
	appShell.classList.add('authenticated');
}

function showAuth() {
	authScreen.style.display = 'grid';
	appShell.classList.remove('authenticated');
}

if (localStorage.getItem('verdant-session')) showWorkspace();

document.querySelectorAll('.auth-tab').forEach((tab) => tab.addEventListener('click', () => {
	authMode = tab.dataset.mode;
	document.querySelectorAll('.auth-tab').forEach((item) => item.classList.toggle('active', item === tab));
	$('auth-title').textContent = authMode === 'signin' ? 'Sign in to your workspace' : 'Create your workspace';
	$('auth-subtitle').textContent = authMode === 'signin' ? 'Monitor your plants and keep their care on track.' : 'Start a calmer, more connected way to care for plants.';
	$('auth-submit').innerHTML = `${authMode === 'signin' ? 'Sign in' : 'Create account'} <span>→</span>`;
	$('name-field').classList.toggle('hidden-field', authMode === 'signin');
	$('forgot-link').style.visibility = authMode === 'signin' ? 'visible' : 'hidden';
	$('auth-message').textContent = '';
}));

$('password-toggle').addEventListener('click', () => {
	const password = $('auth-password');
	password.type = password.type === 'password' ? 'text' : 'password';
	$('password-toggle').textContent = password.type === 'password' ? 'Show' : 'Hide';
});

authForm.addEventListener('submit', (event) => {
	event.preventDefault();
	const password = $('auth-password').value;
	const message = $('auth-message');
	if (password.length < 8) { message.textContent = 'Use at least 8 characters for your password.'; return; }
	localStorage.setItem('verdant-session', JSON.stringify({ email: $('auth-email').value, name: $('auth-name').value || 'Alex' }));
	message.className = 'auth-message success';
	message.textContent = authMode === 'signin' ? 'Signed in. Opening your workspace...' : 'Account created. Opening your workspace...';
	setTimeout(showWorkspace, 350);
});

$('forgot-link').addEventListener('click', (event) => { event.preventDefault(); $('auth-message').textContent = 'Password reset is available in the cloud deployment.'; });
$('logout-button').addEventListener('click', () => { localStorage.removeItem('verdant-session'); showAuth(); });

async function api(path, options = {}) { const response = await fetch(`/api${path}`, { headers: {'Content-Type':'application/json'}, ...options }); if (!response.ok) throw new Error(await response.text()); return response.json(); }
function setText(id, value) { $(id).textContent = value; }
function drawChart(points, threshold) { const svgWidth=700, svgHeight=210, pad=8; if (!points.length) return; const values=points.map(p=>p.soil_moisture); const min=0, max=100; const coords=values.map((v,i)=>[(i/(Math.max(values.length-1,1)))*(svgWidth-pad*2)+pad, svgHeight-pad-(v/max)*(svgHeight-pad*2)]); const line=coords.map((p,i)=>`${i?'L':'M'}${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(' '); const area=`${line} L ${coords.at(-1)[0]},${svgHeight} L ${coords[0][0]},${svgHeight} Z`; $('chart-line').setAttribute('d',line); $('chart-area').setAttribute('d',area); }
function render(data) { const latest=data.latest; const device=data.device; if (!latest) return; setText('plant-device', device.device_id); setText('plant-name', `${device.plant_name} `); $('plant-name').appendChild(document.createElement('span')).className = 'status-dot'; setText('plant-location', device.location); setText('soil-value', `${Math.round(latest.soil_moisture)}%`); setText('temp-value', `${latest.temperature.toFixed(1)}°`); setText('humidity-value', `${Math.round(latest.humidity)}%`); setText('light-value', `${Math.round(latest.light_level)}%`); setText('threshold-label', `${Math.round(device.threshold)}%`); setText('last-seen', new Date(latest.timestamp).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'})); $('soil-bar').style.width=`${latest.soil_moisture}%`; $('auto-toggle').checked=Boolean(device.auto_water); $('threshold').value=Math.round(device.threshold); setText('profile-badge', device.plant_type.toUpperCase()); history=data.history; drawChart(history,device.threshold); const events=$('events'); setText('event-count',data.watering_history.length); events.innerHTML=data.watering_history.length ? data.watering_history.map(e=>`<div class="event"><span class="event-icon">↗</span><div><strong>${e.trigger_type==='automatic'?'Automatic watering':'Manual watering'}</strong><small>${new Date(e.timestamp).toLocaleString()} · ${e.duration_seconds}s pulse</small></div></div>`).join('') : '<div class="empty">No watering events yet. The system will act when soil falls below the threshold.</div>'; const alerts=$('alerts'); setText('alert-count',data.alerts.length); alerts.innerHTML=data.alerts.length ? data.alerts.map(a=>`<div class="alert-item"><span class="alert-mark"></span><div><strong>${a.message}</strong><small>${a.level.toUpperCase()} · ${new Date(a.created_at).toLocaleString()}</small></div></div>`).join('') : '<div class="empty">No active alerts. Your plant is looking good.</div>'; }
function renderDemoPlant(plant) { setText('plant-device', plant.id || activePlantId); setText('plant-name', `${plant.name} `); $('plant-name').appendChild(document.createElement('span')).className = 'status-dot'; setText('plant-location', plant.location); setText('soil-value', `${plant.soil}%`); setText('temp-value', `${plant.temperature.toFixed(1)}°`); setText('humidity-value', `${plant.humidity}%`); setText('light-value', `${plant.light}%`); setText('threshold-label', `${plant.threshold}%`); setText('last-seen', 'profile preview'); $('soil-bar').style.width=`${plant.soil}%`; $('auto-toggle').checked=true; $('threshold').value=plant.threshold; setText('profile-badge', plant.type); $('events').innerHTML='<div class="empty">No watering events recorded for this profile yet.</div>'; $('alerts').innerHTML='<div class="empty">No active alerts. This plant is looking good.</div>'; setText('event-count','0'); setText('alert-count','0'); }
async function refresh(){ if (activePlantId !== deviceId) return; try { render(await api(`/devices/${deviceId}/overview`)); } catch (error) { console.error(error); } }
document.querySelectorAll('.plant-item').forEach((item) => item.addEventListener('click', (event) => { event.preventDefault(); activePlantId = item.dataset.plantId; document.querySelectorAll('.plant-item').forEach((row) => row.classList.toggle('selected', row === item)); $('water-button').disabled = activePlantId !== deviceId; $('water-button').textContent = activePlantId === deviceId ? '↗ Water now' : 'Live device only'; if (activePlantId === deviceId) { refresh(); } else { renderDemoPlant({...plantProfiles[activePlantId], id: activePlantId}); } }));
$('water-button').addEventListener('click', async () => { const button=$('water-button'); button.disabled=true; button.textContent='✓ Water queued'; await api(`/devices/${deviceId}/water`,{method:'POST',body:JSON.stringify({duration_seconds:4})}); setTimeout(()=>{button.disabled=false;button.textContent='↗ Water now';refresh()},1200); });
$('save-threshold').addEventListener('click', async () => { await api(`/devices/${deviceId}/threshold`,{method:'PUT',body:JSON.stringify({threshold:Number($('threshold').value)})}); refresh(); });
$('auto-toggle').addEventListener('change', async (event) => { await api(`/devices/${deviceId}/automation?enabled=${event.target.checked}`,{method:'PUT'}); });
refresh(); setInterval(refresh,5000);
