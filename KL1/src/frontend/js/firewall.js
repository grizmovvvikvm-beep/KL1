// Simple extended firewall UI for aliases and rules (WAN / OVPN via dropdowns)

async function fetchAliases() {
    const res = await fetch('/api/firewall/aliases');
    return res.ok ? res.json() : [];
}

async function fetchRules() {
    const res = await fetch('/api/firewall/rules');
    return res.ok ? res.json() : [];
}

let currentScope = 'WAN';            // 'WAN' or 'OVPN'
let currentOVPNInstance = '';       // empty = all instances

function escapeHtml(s){ if(!s) return ''; return String(s).replace(/[&<>"']/g, m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[m]); }

function renderAliases(list) {
    const tbody = document.querySelector('#aliasesTable tbody');
    if(!tbody) return;
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
            <td class="small">${a.stats && a.stats.hits ? 'hits: ' + (a.stats.hits || 0) : ''}</td>
            <td class="small">${escapeHtml(a.description || '')}</td>
            <td>
                <button class="editAlias" data-id="${a.id}">Edit</button>
                <button class="delAlias" data-id="${a.id}">Del</button>
            </td>
        `;
        tbody.appendChild(tr);
    });
    attachAliasRowHandlers();
    // populate OVPN instance select from aliases of type OpenVPN
    const ovpnSelect = document.getElementById('ovpnInstanceSelect');
    if(ovpnSelect) {
        // keep first option as "all instances"
        const existing = Array.from(ovpnSelect.options).slice(1).map(o=>o.value);
        const instances = list.filter(x=>x.type && x.type.toLowerCase()==='openvpn').map(x=>x.name);
        // remove options not present any more
        Array.from(ovpnSelect.options).forEach(opt=>{
            if(opt.index===0) return;
            if(!instances.includes(opt.value)) ovpnSelect.removeChild(opt);
        });
        // add new instances
        instances.forEach(name=>{
            if(!existing.includes(name)) {
                const opt = document.createElement('option');
                opt.value = name; opt.textContent = name;
                ovpnSelect.appendChild(opt);
            }
        });
    }
}

function renderRules(list) {
    const tbody = document.querySelector('#rulesTable tbody');
    if(!tbody) return;
    tbody.innerHTML = '';
    const filtered = list.filter(r => {
        if (currentScope === 'WAN') return !r.vpn_instance_id;
        if (currentScope === 'OVPN' && !currentOVPNInstance) return r.vpn_instance_id !== null;
        if (currentScope === 'OVPN' && currentOVPNInstance) return r.vpn_instance_name === currentOVPNInstance;
        return true;
    });
    filtered.forEach(r => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><span class="toggle ${r.enabled ? 'on' : ''}"></span></td>
            <td>${escapeHtml(r.name)}</td>
            <td>${escapeHtml(r.action || '')}</td>
            <td>${escapeHtml(r.interface || (r.vpn_instance_name ? 'OpenVPN' : 'WAN'))}</td>
            <td>${escapeHtml(r.direction || 'in')}</td>
            <td>${escapeHtml(r.protocol || '')}</td>
            <td>${escapeHtml(r.source || '')}</td>
            <td>${escapeHtml(r.destination || '')}</td>
            <td>${escapeHtml(r.vpn_instance_name || '')}</td>
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
            if(res.ok) { loadAliases(); loadRules(); }
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

// Alias form (modal)
function openAliasForm(alias = null) {
    const overlay = document.createElement('div'); overlay.className='overlay';
    const card = document.createElement('div'); card.className='form-card';
    overlay.appendChild(card);
    card.innerHTML = `
        <h3>${alias ? 'Edit alias' : 'New alias'}</h3>
        <div class="form-row"><label>Name</label><input id="fa_name" type="text" value="${alias ? escapeHtml(alias.name) : ''}"></div>
        <div class="form-row"><label>Type</label>
            <select id="fa_type"><option>Host</option><option>Network</option><option>URL</option><option>OpenVPN</option></select>
        </div>
        <div class="form-row"><label>Hosts</label><input id="fa_hosts" type="text" value="${alias ? escapeHtml(alias.hosts||'') : ''}"></div>
        <div class="form-row"><label>Categories</label><input id="fa_categories" type="text" value="${alias ? escapeHtml(alias.categories||'') : ''}"></div>
        <div class="form-row"><label>Content</label><textarea id="fa_content">${alias ? escapeHtml(alias.content||'') : ''}</textarea></div>
        <div class="form-row"><label>Description</label><input id="fa_description" type="text" value="${alias ? escapeHtml(alias.description||'') : ''}"></div>
        <div class="form-row"><label>Enabled</label><input id="fa_enabled" type="checkbox" ${alias && alias.enabled===false ? '' : 'checked'}></div>
        <div class="form-actions">
            <button id="fa_cancel">Cancel</button>
            <button id="fa_save">${alias ? 'Save' : 'Create'}</button>
        </div>
    `;
    document.body.appendChild(overlay);
    if(alias) document.getElementById('fa_type').value = alias.type || 'Host';
    document.getElementById('fa_cancel').addEventListener('click', ()=> overlay.remove());
    document.getElementById('fa_save').addEventListener('click', async ()=>{
        const payload = {
            name: document.getElementById('fa_name').value.trim(),
            type: document.getElementById('fa_type').value,
            hosts: document.getElementById('fa_hosts').value.trim(),
            categories: document.getElementById('fa_categories').value.trim(),
            content: document.getElementById('fa_content').value.trim(),
            description: document.getElementById('fa_description').value.trim(),
            enabled: document.getElementById('fa_enabled').checked
        };
        if(!payload.name) return alert('Name required');
        try {
            if(alias && alias.id) {
                await fetch(`/api/firewall/aliases/${alias.id}`, { method: 'PUT', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload) });
            } else {
                const res = await fetch('/api/firewall/aliases', { method: 'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload) });
                if(!res.ok) {
                    const t = await res.text(); alert(t); return;
                }
            }
            overlay.remove();
            await loadAliases();
            await loadRules();
        } catch(err) { alert('Save failed'); overlay.remove(); }
    });
}

// Rule form (modal)
function openRuleForm(rule = null) {
    const overlay = document.createElement('div'); overlay.className='overlay';
    const card = document.createElement('div'); card.className='form-card';
    overlay.appendChild(card);

    const initial = rule || {};
    card.innerHTML = `
        <h3>${rule ? 'Edit rule' : 'New rule'}</h3>
        <div class="form-row"><label>Action</label><select id="r_action"><option>Pass</option><option>Block</option><option>Reject</option></select></div>
        <div class="form-row"><label>Disabled</label><input id="r_disabled" type="checkbox"></div>
        <div class="form-row"><label>Quick</label><input id="r_quick" type="checkbox"></div>
        <div class="form-row"><label>Interface</label><select id="r_interface"><option>WAN</option><option>OpenVPN</option></select></div>
        <div class="form-row"><label>Direction</label><select id="r_direction"><option>in</option><option>out</option></select></div>
        <div class="form-row"><label>TCP/IP Version</label><select id="r_ipver"><option>IPv4</option><option>IPv6</option><option>IPv4+IPv6</option></select></div>
        <div class="form-row"><label>Protocol</label><select id="r_protocol"><option>any</option><option>TCP</option><option>UDP</option><option>TCP/UDP</option></select></div>
        <hr/>
        <div class="form-row"><label>Source / Invert</label><input id="r_source_invert" type="checkbox"></div>
        <div class="form-row"><label>Source</label><input id="r_source" type="text" placeholder="Single host or Network"></div>
        <div class="form-row"><label>Source type</label><select id="r_source_type"><option>Single host or Network</option><option>Alias</option><option>Network</option></select></div>
        <div class="form-row"><label>Destination / Invert</label><input id="r_dest_invert" type="checkbox"></div>
        <div class="form-row"><label>Destination</label><input id="r_destination" type="text" placeholder="Single host or Network"></div>
        <div class="form-row"><label>Destination port range</label><input id="r_port_from" type="text" placeholder="from" style="width:120px"/> <input id="r_port_to" type="text" placeholder="to" style="width:120px"/></div>
        <div class="form-row"><label>Log</label><input id="r_log" type="checkbox"></div>
        <div class="form-row"><label>Category</label><input id="r_category" type="text"></div>
        <div class="form-row"><label>Description</label><input id="r_description" type="text"></div>
        <div class="form-row"><label>No XMLRPC Sync</label><input id="r_noxmlrpc" type="checkbox"></div>
        <div class="form-row"><label>Schedule</label><select id="r_schedule"><option>none</option></select></div>
        <div class="form-row"><label>Gateway</label><select id="r_gateway"><option>default</option></select></div>
        <div class="form-actions"><button id="r_cancel">Cancel</button><button id="r_save">${rule ? 'Save' : 'Create'}</button></div>
        <div class="small-muted" style="margin-top:8px">Rule Information will be provided by server (created/updated).</div>
    `;
    document.body.appendChild(overlay);

    // set initial values
    document.getElementById('r_action').value = initial.action ? capitalize(initial.action) : 'Pass';
    document.getElementById('r_disabled').checked = initial.enabled === false;
    document.getElementById('r_quick').checked = !!initial.quick;
    document.getElementById('r_interface').value = initial.interface || (initial.vpn_instance_name ? 'OpenVPN' : 'WAN');
    document.getElementById('r_direction').value = initial.direction || 'in';
    document.getElementById('r_ipver').value = initial.ipver || 'IPv4+IPv6';
    document.getElementById('r_protocol').value = initial.protocol || 'TCP/UDP';
    document.getElementById('r_source').value = initial.source || '';
    document.getElementById('r_destination').value = initial.destination || '';
    document.getElementById('r_port_from').value = (initial.port_from || '');
    document.getElementById('r_port_to').value = (initial.port_to || '');
    document.getElementById('r_log').checked = !!initial.log;
    document.getElementById('r_category').value = initial.category || '';
    document.getElementById('r_description').value = initial.description || '';
    document.getElementById('r_noxmlrpc').checked = !!initial.noxmlrpc;

    document.getElementById('r_cancel').addEventListener('click', ()=> overlay.remove());
    document.getElementById('r_save').addEventListener('click', async ()=>{
        const payload = {
            name: initial.name || (document.getElementById('r_description').value || 'rule'),
            action: document.getElementById('r_action').value,
            enabled: !document.getElementById('r_disabled').checked,
            quick: document.getElementById('r_quick').checked,
            interface: document.getElementById('r_interface').value,
            direction: document.getElementById('r_direction').value,
            ipver: document.getElementById('r_ipver').value,
            protocol: document.getElementById('r_protocol').value,
            source: document.getElementById('r_source').value,
            source_type: document.getElementById('r_source_type').value,
            destination: document.getElementById('r_destination').value,
            port_from: document.getElementById('r_port_from').value,
            port_to: document.getElementById('r_port_to').value,
            log: document.getElementById('r_log').checked,
            category: document.getElementById('r_category').value,
            description: document.getElementById('r_description').value,
            noxmlrpc: document.getElementById('r_noxmlrpc').checked,
            schedule: document.getElementById('r_schedule').value,
            gateway: document.getElementById('r_gateway').value,
            vpn_instance_id: null,
            vpn_instance_name: null
        };
        // if scope is OVPN and specific instance selected, set vpn_instance_name
        if (currentScope === 'OVPN' && currentOVPNInstance) payload.vpn_instance_name = currentOVPNInstance;

        try {
            if (initial.id) {
                await fetch(`/api/firewall/rules/${initial.id}`, { method:'PUT', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload) });
            } else {
                await fetch('/api/firewall/rules', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload) });
            }
            overlay.remove();
            loadRules();
        } catch(e){ alert('Save failed'); overlay.remove(); }
    });
}

function capitalize(s){ return String(s).charAt(0).toUpperCase()+String(s).slice(1); }

async function loadAliases() {
    const list = await fetchAliases();
    renderAliases(list);
}

async function loadRules() {
    const list = await fetchRules();
    renderRules(list);
}

function initFirewallUI(){
    // Aliases
    const addAliasBtn = document.getElementById('addAliasBtn');
    if(addAliasBtn) addAliasBtn.addEventListener('click', ()=> openAliasForm());

    // Rules scope select
    const scopeSelect = document.getElementById('rulesScope');
    const ovpnSelect = document.getElementById('ovpnInstanceSelect');
    if(scopeSelect) {
        scopeSelect.value = currentScope;
        scopeSelect.addEventListener('change', ()=> {
            currentScope = scopeSelect.value;
            if(currentScope === 'OVPN') {
                if(ovpnSelect) ovpnSelect.disabled = false;
            } else {
                if(ovpnSelect) { ovpnSelect.disabled = true; ovpnSelect.value = ''; currentOVPNInstance = ''; }
            }
            loadRules();
        });
    }
    if(ovpnSelect) {
        ovpnSelect.addEventListener('change', ()=> {
            currentOVPNInstance = ovpnSelect.value || '';
            loadRules();
        });
    }

    const addRuleBtn = document.getElementById('addRuleGlobalBtn');
    if(addRuleBtn) addRuleBtn.addEventListener('click', ()=> openRuleForm());

    loadAliases();
    loadRules();
}

window.initFirewallUI = initFirewallUI;

document.addEventListener('DOMContentLoaded', ()=> {
    if(typeof initFirewallUI === 'function') initFirewallUI();
});