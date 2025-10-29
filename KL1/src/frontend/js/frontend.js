// ...existing code...
/*
  Simple firewall UI client.
  Endpoints used:
    GET  /api/firewall/aliases
    POST /api/firewall/aliases
    PUT  /api/firewall/aliases/<id>
    DELETE /api/firewall/aliases/<id>

    GET  /api/firewall/rules
    POST /api/firewall/rules
    PUT  /api/firewall/rules/<id>
    DELETE /api/firewall/rules/<id>
*/

async function fetchAliases() {
    const res = await fetch('/api/firewall/aliases');
    return res.ok ? res.json() : [];
}

async function fetchRules() {
    const res = await fetch('/api/firewall/rules');
    return res.ok ? res.json() : [];
}

function renderAliases(list) {
    const tbody = document.querySelector('#aliasesTable tbody');
    tbody.innerHTML = '';
    list.forEach(a => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><span class="toggle ${a.enabled ? 'on' : ''}"></span></td>
            <td>${escapeHtml(a.name)}</td>
            <td>${escapeHtml(a.type)}</td>
            <td>${escapeHtml(a.hosts || '')}</td>
            <td>${escapeHtml(a.categories || '')}</td>
            <td>${escapeHtml(a.content || '')}</td>
            <td class="small">${a.stats ? 'hits: ' + (a.stats.hits || 0) : ''}</td>
            <td class="small">${escapeHtml(a.description || '')}</td>
            <td>
                <button class="editAlias" data-id="${a.id}">Edit</button>
                <button class="delAlias" data-id="${a.id}">Del</button>
            </td>
        `;
        tbody.appendChild(tr);
    });
    attachAliasRowHandlers();
}

function renderRules(list) {
    // create rules table if not exists
    let container = document.getElementById('firewallRulesContainer');
    if(!container) {
        container = document.createElement('div');
        container.id = 'firewallRulesContainer';
        container.className = 'card';
        container.style.marginTop = '16px';
        const html = `
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
                <div class="small">Правила фаервола (система / VPN)</div>
                <div><button id="addRuleBtn">Добавить правило</button></div>
            </div>
            <div style="overflow:auto">
                <table id="rulesTable">
                    <thead>
                        <tr>
                            <th>Enabled</th><th>Name</th><th>Action</th><th>Protocol</th>
                            <th>Source</th><th>Destination</th><th>VPN Instance</th><th>Description</th><th></th>
                        </tr>
                    </thead>
                    <tbody></tbody>
                </table>
            </div>
        `;
        container.innerHTML = html;
        document.querySelector('main .main > section')?.after(container) || document.querySelector('.main').appendChild(container);
        document.getElementById('addRuleBtn').addEventListener('click', ()=> openRuleForm());
    }
    const tbody = document.querySelector('#rulesTable tbody');
    tbody.innerHTML = '';
    list.forEach(r => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><span class="toggle ${r.enabled ? 'on' : ''}"></span></td>
            <td>${escapeHtml(r.name)}</td>
            <td>${escapeHtml(r.action)}</td>
            <td>${escapeHtml(r.protocol || '')}</td>
            <td>${escapeHtml(r.source || '')}</td>
            <td>${escapeHtml(r.destination || '')}</td>
            <td>${escapeHtml(r.vpn_instance_name || '')}</td>
            <td class="small">${escapeHtml(r.description || '')}</td>
            <td><button class="editRule" data-id="${r.id}">Edit</button> <button class="delRule" data-id="${r.id}">Del</button></td>
        `;
        tbody.appendChild(tr);
    });
    attachRuleRowHandlers();
}

function attachAliasRowHandlers() {
    document.querySelectorAll('.editAlias').forEach(btn=>{
        btn.addEventListener('click', async ()=> {
            const id = btn.dataset.id;
            const res = await fetch(`/api/firewall/aliases/${id}`);
            if(res.ok) {
                const alias = await res.json();
                openAliasForm(alias);
            } else alert('Не удалось загрузить алиас');
        });
    });
    document.querySelectorAll('.delAlias').forEach(btn=>{
        btn.addEventListener('click', async ()=> {
            if(!confirm('Удалить алиас?')) return;
            const id = btn.dataset.id;
            const res = await fetch(`/api/firewall/aliases/${id}`, { method: 'DELETE' });
            if(res.ok) loadAliases();
            else alert('Ошибка удаления');
        });
    });
}

function attachRuleRowHandlers() {
    document.querySelectorAll('.editRule').forEach(btn=>{
        btn.addEventListener('click', async ()=> {
            const id = btn.dataset.id;
            const res = await fetch(`/api/firewall/rules/${id}`);
            if(res.ok) {
                const rule = await res.json();
                openRuleForm(rule);
            } else alert('Не удалось загрузить правило');
        });
    });
    document.querySelectorAll('.delRule').forEach(btn=>{
        btn.addEventListener('click', async ()=> {
            if(!confirm('Удалить правило?')) return;
            const id = btn.dataset.id;
            const res = await fetch(`/api/firewall/rules/${id}`, { method: 'DELETE' });
            if(res.ok) loadRules();
            else alert('Ошибка удаления');
        });
    });
}

async function loadAliases() {
    const list = await fetchAliases();
    renderAliases(list);
}

async function loadRules() {
    const list = await fetchRules();
    renderRules(list);
}

function openAliasForm(alias = null) {
    // minimal prompt-based form for now
    const name = prompt('Name:', alias ? alias.name : '');
    if(!name) return;
    const type = prompt('Type (Host/Network/URL):', alias ? alias.type : 'Host');
    const hosts = prompt('Hosts (comma separated):', alias ? alias.hosts : '');
    const categories = prompt('Categories (comma separated):', alias ? alias.categories : '');
    const content = prompt('Content (raw):', alias ? alias.content : hosts);
    const description = prompt('Description:', alias ? alias.description : '');
    const enabled = confirm('Enable alias?');

    const payload = { name, type, hosts, categories, content, description, enabled };

    if(alias && alias.id) {
        fetch(`/api/firewall/aliases/${alias.id}`, {
            method: 'PUT',
            headers: {'Content-Type':'application/json'},
            body: JSON.stringify(payload)
        }).then(r=> { if(r.ok) loadAliases(); else r.text().then(t=>alert(t)); });
    } else {
        fetch('/api/firewall/aliases', {
            method: 'POST',
            headers: {'Content-Type':'application/json'},
            body: JSON.stringify(payload)
        }).then(r=> { if(r.ok) loadAliases(); else r.text().then(t=>alert(t)); });
    }
}

function openRuleForm(rule = null) {
    const name = prompt('Name:', rule ? rule.name : '');
    if(!name) return;
    const action = prompt('Action (allow/deny):', rule ? rule.action : 'allow');
    const protocol = prompt('Protocol (tcp/udp/any):', rule ? rule.protocol : 'any');
    const source = prompt('Source (ip/alias):', rule ? rule.source : '');
    const destination = prompt('Destination (ip/alias):', rule ? rule.destination : '');
    const vpn_instance_id = prompt('VPN instance id (leave empty for system rule):', rule ? (rule.vpn_instance_id || '') : '');
    const description = prompt('Description:', rule ? rule.description : '');
    const enabled = confirm('Enable rule?');

    const payload = { name, action, protocol, source, destination, vpn_instance_id: vpn_instance_id || null, description, enabled };

    if(rule && rule.id) {
        fetch(`/api/firewall/rules/${rule.id}`, {
            method: 'PUT',
            headers: {'Content-Type':'application/json'},
            body: JSON.stringify(payload)
        }).then(r=> { if(r.ok) loadRules(); else r.text().then(t=>alert(t)); });
    } else {
        fetch('/api/firewall/rules', {
            method: 'POST',
            headers: {'Content-Type':'application/json'},
            body: JSON.stringify(payload)
        }).then(r=> { if(r.ok) loadRules(); else r.text().then(t=>alert(t)); });
    }
}

function escapeHtml(s){ if(!s) return ''; return String(s).replace(/[&<>"']/g, function(m){return ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[m];}); }

// init when firewall view shown
function initFirewallUI(){
    // attach addAliasBtn is in page already
    document.getElementById('addAliasBtn').addEventListener('click', ()=> openAliasForm());
    loadAliases();
    loadRules();
}

// export for index.html
window.initFirewallUI = initFirewallUI;