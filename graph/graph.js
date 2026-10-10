// Color Palette mapping to node_types 
const colorMap = {
    TICKER: { background: '#c586c0', border: '#a05c9a', highlight: '#d197cd' },
    MACRO: { background: '#569cd6', border: '#357ebd', highlight: '#73b3e6' },
    EVENT: { background: '#ce9178', border: '#a6684e', highlight: '#dca690' },
    COMPANY: { background: '#4ec9b0', border: '#30a18a', highlight: '#6addc4' }
};

// Data Storage
let mockNodes = [];
let mockEdges = [];
let nodeDegree = {};

const nodes = new vis.DataSet();
const edges = new vis.DataSet();

const SUPABASE_URL = "https://jqzlmzbvaesczarqptye.supabase.co";
const SUPABASE_KEY = "sb_publishable_wXUovp36dvd_VwdX-U8ecg_P-OrGwEb";
const supabaseClient = window.supabase.createClient(SUPABASE_URL, SUPABASE_KEY);
const backend_url = "https://vonika-git-110018515227.us-central1.run.app/api";

async function loadGraphData() {
    const headers = { 
        "apikey": SUPABASE_KEY, 
        "Authorization": `Bearer ${SUPABASE_KEY}` 
    };

    try {
        const [nodesRes, edgesRes] = await Promise.all([
            fetch(`${SUPABASE_URL}/rest/v1/kg_nodes?select=*`, { headers }),
            fetch(`${SUPABASE_URL}/rest/v1/kg_edges?select=*`, { headers })
        ]);
        
        if (!nodesRes.ok || !edgesRes.ok) {
            console.error("Lỗi tải dữ liệu từ Supabase");
            return;
        }

        const dbNodes = await nodesRes.json();
        const dbEdges = await edgesRes.json();
        
        mockNodes = dbNodes.map(n => ({
            id: n.id,
            label: n.name,
            group: n.node_type,
            aliases: n.aliases || []
        }));
        
        mockEdges = dbEdges.map(e => {
            let label = (e.label || "Tác động").normalize('NFC').trim();
            return {
                id: e.id,
                from: e.source_node_id,
                to: e.target_node_id,
                label: label,
                relation: (e.relation || "").normalize('NFC'),
                evidence: (e.evidence || "").normalize('NFC'),
                source_files: e.source_files || []
            };
        });

        // Deduplicate mockEdges by ID just in case to prevent vis.js errors
        const uniqueEdges = new Map();
        mockEdges.forEach(e => {
            if (!uniqueEdges.has(e.id)) {
                uniqueEdges.set(e.id, e);
            }
        });
        mockEdges = Array.from(uniqueEdges.values());


        
        nodeDegree = {};
        mockEdges.forEach(e => {
            nodeDegree[e.from] = (nodeDegree[e.from] || 0) + 1;
            nodeDegree[e.to] = (nodeDegree[e.to] || 0) + 1;
        });
        
        setTimeout(() => {
            network.fit({ animation: { duration: 1000, easingFunction: 'easeInOutQuad' } });
        }, 1500);
        
        nodes.add(mockNodes.map(node => ({
            id: node.id,
            label: node.label,
            group: node.group,
            shape: 'dot',
            size: 12 + (nodeDegree[node.id] || 0) * 4,
            font: { color: '#e0e0e0', size: 13, face: 'Inter', strokeWidth: 3, strokeColor: '#111111' },
            color: {
                background: colorMap[node.group].background,
                border: colorMap[node.group].border,
                highlight: { background: colorMap[node.group].highlight, border: '#ffffff' }
            },
            borderWidth: 1,
            shadow: { enabled: false }
        })));
        
        edges.add(mockEdges.map(edge => {
            const style = getEdgeStyle(edge.label);
            return {
                id: edge.id,
                from: edge.from,
                to: edge.to,
                label: edge.label,
                font: { color: 'transparent', size: 11, face: 'Inter', align: 'middle', strokeWidth: 0 },
                color: { color: style.color, highlight: style.highlight, hover: style.hover, inherit: false },
                arrows: style.arrows || { to: { enabled: true, scaleFactor: 0.8 } },
                width: style.width,
                dashes: style.dashes,
                smooth: { type: 'dynamic' },
                originalColor: style.color,
                source_files: edge.source_files
            };
        }));
        
        const allSources = new Set();
        mockEdges.forEach(e => {
            if (e.source_files) e.source_files.forEach(s => allSources.add(s));
        });
        
        // Convert Set to Array and Sort Descending (Newest to Oldest)
        const sortedSources = Array.from(allSources).sort((a, b) => {
            const dateMatchA = a.match(/(\d{2})-(\d{2})-(\d{4})/);
            const dateMatchB = b.match(/(\d{2})-(\d{2})-(\d{4})/);
            if (dateMatchA && dateMatchB) {
                const dateA = new Date(dateMatchA[3], dateMatchA[2] - 1, dateMatchA[1]);
                const dateB = new Date(dateMatchB[3], dateMatchB[2] - 1, dateMatchB[1]);
                return dateB - dateA;
            }
            return b.localeCompare(a); // Fallback string sort descending
        });

        const sourceContainer = document.getElementById('source-filters');
        if (sourceContainer) {
            sourceContainer.innerHTML = '';
            sortedSources.forEach(s => {
                let cb = document.createElement('label');
                cb.className = 'filter-item';
                cb.innerHTML = `<input type="checkbox" value="${s}" checked class="source-filter"> ${s}`;
                cb.querySelector('input').addEventListener('change', applyFilters);
                sourceContainer.appendChild(cb);
            });
        }

        applyFilters();
        updateSidebarCounts();
        
        const urlParams = new URLSearchParams(window.location.search);
        const focusNode = urlParams.get('node');
        if (focusNode && mockNodes.some(n => n.id == focusNode)) {
            network.selectNodes([focusNode]);
            network.emit('click', {nodes: [focusNode], edges: []});
        }
    } catch (err) {
        console.error("Lỗi:", err);
    }
}


// Determine Edge Styles
const GLOBAL_POSITIVE = ['Thúc đẩy', 'Hưởng lợi', 'Tác động tích cực', 'Tích cực', 'Làm tăng'];
const GLOBAL_NEGATIVE = ['Gây áp lực', 'Tác động tiêu cực', 'Tiêu cực', 'Làm giảm'];
const GLOBAL_STRUCTURE = ['Bao gồm', 'Sở hữu', 'Cấu trúc', 'Hành động'];

const EDGE_VERBS = {
  "Sở hữu": { forward: "sở hữu", backward: "là công ty con của" },
  "Bao gồm": { forward: "bao gồm", backward: "thuộc" },
  "Hành động": { forward: "thực hiện", backward: "được thực hiện bởi" },
  "Tác động tích cực": { forward: "tác động tích cực đến", backward: "được hưởng lợi từ" },
  "Tác động tiêu cực": { forward: "tác động tiêu cực đến", backward: "bị ảnh hưởng bởi" },
  "Thúc đẩy": { forward: "thúc đẩy", backward: "được thúc đẩy bởi" },
  "Làm tăng": { forward: "làm tăng", backward: "bị làm tăng bởi" },
  "Gây áp lực": { forward: "gây áp lực lên", backward: "chịu áp lực từ" },
  "Làm giảm": { forward: "làm giảm", backward: "bị làm giảm bởi" },
  "Hưởng lợi": { forward: "được hưởng lợi từ", backward: "mang lại lợi ích cho" }
};

const ROLE_BADGES = {
  "Sở hữu": { source: "MẸ", target: "CON" },
  "Bao gồm": { source: "TỔNG", target: "THÀNH PHẦN" }
};

function getEdgeStyle(label) {
    if (GLOBAL_POSITIVE.includes(label)) {
        return { color: '#4caf50', width: 2, hover: '#81c784', highlight: '#81c784', dashes: false };
    } else if (GLOBAL_NEGATIVE.includes(label)) {
        return { color: '#f44336', width: 2, hover: '#e57373', highlight: '#e57373', dashes: false };
    } else if (GLOBAL_STRUCTURE.includes(label)) {
        return { color: '#888888', width: 1.5, hover: '#aaaaaa', highlight: '#ffffff', dashes: [5, 5], arrows: { to: { enabled: true, type: 'diamond', scaleFactor: 1.2 } } };
    } else {
        return { color: 'rgba(255,255,255,0.2)', width: 1, hover: 'rgba(255,255,255,0.6)', highlight: 'rgba(255,255,255,0.8)', dashes: false };
    }
}


// Configuration for Vis.js Network
const container = document.getElementById('graph-container');
const data = { nodes: nodes, edges: edges };
const options = {
    groups: {
        TICKER: { color: { background: colorMap['TICKER'].background, border: colorMap['TICKER'].border, highlight: { background: colorMap['TICKER'].highlight, border: '#ffffff' } } },
        MACRO: { color: { background: colorMap['MACRO'].background, border: colorMap['MACRO'].border, highlight: { background: colorMap['MACRO'].highlight, border: '#ffffff' } } },
        EVENT: { color: { background: colorMap['EVENT'].background, border: colorMap['EVENT'].border, highlight: { background: colorMap['EVENT'].highlight, border: '#ffffff' } } },
        COMPANY: { color: { background: colorMap['COMPANY'].background, border: colorMap['COMPANY'].border, highlight: { background: colorMap['COMPANY'].highlight, border: '#ffffff' } } }
    },
    interaction: {
        hover: true,
        tooltipDelay: 200,
        zoomView: true,
        dragView: true
    },
    physics: {
        forceAtlas2Based: {
            gravitationalConstant: -100,
            centralGravity: 0.01,
            springLength: 200,
            springConstant: 0.08
        },
        maxVelocity: 50,
        solver: 'forceAtlas2Based',
        timestep: 0.35,
        stabilization: { iterations: 150 }
    }
};

// Initialize Network
const network = new vis.Network(container, data, options);
window.network = network;

// UI Interaction Logic

const popup = document.getElementById('info-popup');
const popupTitle = document.getElementById('popup-title');
const popupBadge = document.getElementById('popup-badge');
const popupContent = document.getElementById('popup-content');
const closeBtn = document.getElementById('close-popup');

const popupFooter = document.getElementById('popup-footer');

function showPopup(type, dataObj) {
    if(type === 'NODE') {
        popupFooter.style.display = 'block';
        window.selectedNodeId = dataObj.id;
        const url = new URL(window.location);
        url.searchParams.set('node', dataObj.id);
        url.searchParams.delete('edge');
        window.history.replaceState({}, '', url);
        
        const badges = { TICKER: 'Mã Chứng Khoán', MACRO: 'Vĩ Mô', EVENT: 'Sự Kiện', COMPANY: 'Doanh Nghiệp' };
        popupTitle.innerText = dataObj.label;
        popupTitle.style.color = 'var(--text-main)'; // reset color
        popupBadge.innerText = badges[dataObj.group] || dataObj.group;
        popupBadge.style.color = colorMap[dataObj.group].highlight;
        popupBadge.style.borderColor = 'var(--panel-border)';
        popupBadge.style.background = '#111111';
        
        popupFooter.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center; background: rgba(255,255,255,0.04); padding: 14px 16px; border-radius: var(--radius-md); border: 1px solid var(--panel-border);">
                <div>
                    <span style="font-size: 11px; color: var(--text-muted); display: block; margin-bottom: 8px; text-transform: uppercase; font-weight: 600; letter-spacing: 0.05em;">Mở rộng lân cận</span>
                    <div style="display: flex; gap: 6px;">
                        <button class="scenario-btn" style="padding: 6px 10px; border-radius: 16px; font-size: 11px;" onclick="highlightConnections(window.selectedNodeId, 1)">1 Bước</button>
                        <button class="scenario-btn" style="padding: 6px 10px; border-radius: 16px; font-size: 11px;" onclick="highlightConnections(window.selectedNodeId, 2)">2 Bước</button>
                        <button class="scenario-btn" style="padding: 6px 10px; border-radius: 16px; font-size: 11px;" onclick="highlightConnections(window.selectedNodeId, 3)">3 Bước</button>
                    </div>
                </div>
                <button class="vonika-ask-btn" onclick="askVonika('NODE', '${dataObj.id}')">
                    <i class="fa-brands fa-facebook-messenger"></i> Hỏi Vonika
                </button>
            </div>
        `;
        
        let html = `<p><strong>Tên khác:</strong> ${dataObj.aliases && dataObj.aliases.length ? dataObj.aliases.join(', ') : 'Không có'}</p>`;
        
        // Find connected edges
        const inEdges = mockEdges.filter(e => e.to === dataObj.id);
        const outEdges = mockEdges.filter(e => e.from === dataObj.id);
        
        const structureLabels = ['Bao gồm', 'Công ty mẹ'];
        const inImpact = inEdges.filter(e => !structureLabels.includes(e.label));
        const outImpact = outEdges.filter(e => !structureLabels.includes(e.label));
        const structureEdges = mockEdges.filter(e => (e.from === dataObj.id || e.to === dataObj.id) && structureLabels.includes(e.label));
        
        if (inImpact.length > 0) {
            html += `<p style="margin-top: 12px; font-weight: 500; color: #fff;">Nhận tác động:</p><ul style="padding-left: 16px; font-size: 13px; color: var(--text-muted); margin-top: 6px;">`;
            inImpact.forEach(e => {
                const source = mockNodes.find(n => n.id === e.from);
                const isNeg = ['Gây áp lực', 'Tác động tiêu cực'].includes(e.label);
                const icon = isNeg ? '<span style="color:#f44336">▼</span>' : '<span style="color:#4caf50">▲</span>';
                
                let actionText = 'Bởi';
                if (e.label === 'Thúc đẩy') actionText = 'Được thúc đẩy bởi';
                else if (e.label === 'Hưởng lợi') actionText = 'Hưởng lợi từ';
                else if (e.label === 'Tác động tích cực') actionText = 'Chịu tác động tích cực từ';
                else if (e.label === 'Gây áp lực') actionText = 'Chịu áp lực từ';
                else if (e.label === 'Tác động tiêu cực') actionText = 'Chịu tác động tiêu cực từ';

                html += `<li style="margin-bottom: 4px;">${icon} <span style="color:#fff;">${actionText}</span> <span style="color:${colorMap[source.group].highlight}; cursor:pointer;" onclick="network.selectNodes(['${source.id}']); network.emit('click', {nodes: ['${source.id}'], edges: []})">${source.label}</span></li>`;
            });
            html += `</ul>`;
        }

        if (outImpact.length > 0) {
            html += `<p style="margin-top: 12px; font-weight: 500; color: #fff;">Gây tác động:</p><ul style="padding-left: 16px; font-size: 13px; color: var(--text-muted); margin-top: 6px;">`;
            outImpact.forEach(e => {
                const target = mockNodes.find(n => n.id === e.to);
                const isNeg = ['Gây áp lực', 'Tác động tiêu cực'].includes(e.label);
                const icon = isNeg ? '<span style="color:#f44336">▼</span>' : '<span style="color:#4caf50">▲</span>';
                
                let actionText = 'Tác động đến';
                if (e.label === 'Thúc đẩy') actionText = 'Thúc đẩy';
                else if (e.label === 'Hưởng lợi') actionText = 'Mang lại lợi ích cho';
                else if (e.label === 'Tác động tích cực') actionText = 'Tác động tích cực đến';
                else if (e.label === 'Gây áp lực') actionText = 'Gây áp lực lên';
                else if (e.label === 'Tác động tiêu cực') actionText = 'Tác động tiêu cực đến';

                html += `<li style="margin-bottom: 4px;">${icon} <span style="color:#fff;">${actionText}</span> <span style="color:${colorMap[target.group].highlight}; cursor:pointer;" onclick="network.selectNodes(['${target.id}']); network.emit('click', {nodes: ['${target.id}'], edges: []})">${target.label}</span></li>`;
            });
            html += `</ul>`;
        }

        if (structureEdges.length > 0) {
            html += `<p style="margin-top: 12px; font-weight: 500; color: #fff;">Liên quan:</p><ul style="padding-left: 16px; font-size: 13px; color: var(--text-muted); margin-top: 6px;">`;
            structureEdges.forEach(e => {
                const isOut = e.from === dataObj.id;
                const other = mockNodes.find(n => n.id === (isOut ? e.to : e.from));
                
                let relText = '';
                if (isOut) {
                    if (e.label === 'Bao gồm') relText = 'Bao gồm';
                    else if (e.label === 'Công ty mẹ') relText = 'Là công ty mẹ của';
                    else relText = `Liên kết đến`;
                } else {
                    if (e.label === 'Bao gồm') relText = 'Trực thuộc';
                    else if (e.label === 'Công ty mẹ') relText = 'Là công ty con của';
                    else relText = `Liên kết từ`;
                }

                html += `<li style="margin-bottom: 4px;"><span style="color:#fff;">${relText}</span> <span style="color:${colorMap[other.group].highlight}; cursor:pointer;" onclick="network.selectNodes(['${other.id}']); network.emit('click', {nodes: ['${other.id}'], edges: []})">${other.label}</span></li>`;
            });
            html += `</ul>`;
        }
        
        popupContent.innerHTML = html;
    } 
    else if(type === 'EDGE') {
        const url = new URL(window.location);
        url.searchParams.set('edge', dataObj.id);
        url.searchParams.delete('node');
        window.history.replaceState({}, '', url);
        
        const fromNode = mockNodes.find(n => n.id === dataObj.from);
        const toNode = mockNodes.find(n => n.id === dataObj.to);
        
        const positiveEdges = ['Thúc đẩy', 'Hưởng lợi', 'Tác động tích cực', 'Tích cực'];
        const negativeEdges = ['Gây áp lực', 'Tác động tiêu cực', 'Tiêu cực'];
        
        let edgeNature = 'Cấu trúc';
        let edgeColor = '#94a3b8';
        let natureIcon = '<i class="fa-solid fa-link" style="margin-right:4px;"></i>';
        
        if (positiveEdges.includes(dataObj.label)) {
            edgeNature = 'Tích cực';
            edgeColor = '#4caf50';
            natureIcon = '<i class="fa-solid fa-arrow-trend-up" style="margin-right:4px;"></i>';
        } else if (negativeEdges.includes(dataObj.label)) {
            edgeNature = 'Tiêu cực';
            edgeColor = '#f44336';
            natureIcon = '<i class="fa-solid fa-arrow-trend-down" style="margin-right:4px;"></i>';
        }
        
        const eLabel = dataObj.label;
        const verbFwd = EDGE_VERBS[eLabel]?.forward ?? eLabel.toLowerCase();
        const verbBwd = EDGE_VERBS[eLabel]?.backward ?? `liên quan tới`;
        
        popupTitle.innerText = `${fromNode.label} ${verbFwd} ${toNode.label}`;
        popupTitle.style.color = 'var(--text-main)';
        popupTitle.style.fontSize = '16px';
        popupTitle.style.lineHeight = '1.4';
        
        popupBadge.innerHTML = `${natureIcon}${edgeNature}`;
        popupBadge.style.color = edgeColor;
        popupBadge.style.borderColor = edgeColor;
        popupBadge.style.background = 'rgba(0,0,0,0.3)';
        
        let html = '';
        
        if (dataObj.relation && !GLOBAL_STRUCTURE.includes(eLabel)) {
            html += `<div style="font-size: 13px; color: var(--text-muted); margin-bottom: 12px; display: flex; align-items: flex-start; gap: 8px;">
                <span style="display:inline-block; width: 4px; height: 16px; background: ${edgeColor}; border-radius: 2px; flex-shrink: 0; margin-top: 2px;"></span> 
                <span><strong>Bản chất:</strong> ${dataObj.relation}</span>
            </div>`;
        }
        
        const srcBadge = ROLE_BADGES[eLabel]?.source;
        const tgtBadge = ROLE_BADGES[eLabel]?.target;
        
        html += `
            <div style="font-size: 12.5px; color: var(--text-muted); text-align: center; margin-bottom: 8px; font-style: italic;">${toNode.label} ${verbBwd} ${fromNode.label}</div>
            <div style="display: flex; align-items: center; justify-content: center; gap: 10px; margin-bottom: 20px; background: rgba(0,0,0,0.2); padding: 12px 16px; border-radius: var(--radius-sm); border: 1px solid var(--panel-border);">
                <div style="text-align: center;">
                    <div onclick="network.selectNodes(['${fromNode.id}']); network.emit('click', {nodes: ['${fromNode.id}'], edges: []})" style="cursor: pointer; display: flex; align-items: center; gap: 8px; background: rgba(255,255,255,0.05); padding: 6px 12px; border-radius: 16px; font-size: 13px; font-weight: 500; transition: background 0.2s; max-width: 160px;" onmouseover="this.style.background='rgba(255,255,255,0.1)'" onmouseout="this.style.background='rgba(255,255,255,0.05)'" title="${fromNode.label.replace(/"/g, '&quot;')}">
                        <span style="width: 8px; height: 8px; border-radius: 50%; background: ${colorMap[fromNode.group].highlight}; display: inline-block; flex-shrink: 0;"></span>
                        <span style="color:#f4f4f5; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${fromNode.label}</span>
                    </div>
                    ${srcBadge ? `<div style="font-size: 10px; font-weight: bold; margin-top: 6px; color: ${edgeColor}; letter-spacing: 0.05em;">${srcBadge}</div>` : ''}
                </div>
                <span style="color:#666; font-size: 14px;"><i class="fa-solid fa-arrow-right"></i></span>
                <div style="text-align: center;">
                    <div onclick="network.selectNodes(['${toNode.id}']); network.emit('click', {nodes: ['${toNode.id}'], edges: []})" style="cursor: pointer; display: flex; align-items: center; gap: 8px; background: rgba(255,255,255,0.05); padding: 6px 12px; border-radius: 16px; font-size: 13px; font-weight: 500; transition: background 0.2s; max-width: 160px;" onmouseover="this.style.background='rgba(255,255,255,0.1)'" onmouseout="this.style.background='rgba(255,255,255,0.05)'" title="${toNode.label.replace(/"/g, '&quot;')}">
                        <span style="width: 8px; height: 8px; border-radius: 50%; background: ${colorMap[toNode.group].highlight}; display: inline-block; flex-shrink: 0;"></span>
                        <span style="color:#f4f4f5; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${toNode.label}</span>
                    </div>
                    ${tgtBadge ? `<div style="font-size: 10px; font-weight: bold; margin-top: 6px; color: ${edgeColor}; letter-spacing: 0.05em;">${tgtBadge}</div>` : ''}
                </div>
            </div>
        `;
        
        if(dataObj.evidence) {
            html += `
                <div class="evidence-box" style="border-left-color: ${edgeColor};">
                    "${dataObj.evidence}"
                </div>
            `;
        }

        if(dataObj.source_files && dataObj.source_files.length > 0) {
            html += `<p style="margin-top: 12px; font-weight: 500; font-size: 12px; color: #aaa; margin-bottom: 6px;">${dataObj.source_files.length} nguồn tài liệu:</p>`;
            html += `<div class="source-tags">`;
            dataObj.source_files.forEach(file => {
                html += `<span class="source-tag" style="display: inline-flex; align-items: center; gap: 6px; background: #111; color: #888; border: 1px solid #333; padding: 4px 8px; border-radius: 4px; font-size: 11px;"><i class="fa-solid fa-file-pdf" style="color: #e53935;"></i> ${file}</span>`;
            });
            html += `</div>`;
        } else {
            html += `<p style="margin-top: 12px; font-size: 12px; color: #888; font-style: italic;"><i class="fa-solid fa-link" style="margin-right: 4px;"></i> Quan hệ cấu trúc, không cần nguồn dẫn.</p>`;
        }
        
        popupContent.innerHTML = html;
        
        popupFooter.style.display = 'block';
        popupFooter.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center; background: rgba(255,255,255,0.04); padding: 12px 14px; border-radius: var(--radius-md); border: 1px solid var(--panel-border); margin-bottom: 12px;">
                <span style="font-size: 12px; color: var(--text-muted); font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;">Hành động mở rộng:</span>
                <button class="vonika-ask-btn" onclick="askVonika('EDGE', '${dataObj.id}')">
                    <i class="fa-brands fa-facebook-messenger"></i> Hỏi Vonika
                </button>
            </div>
            <div style="display: flex; gap: 8px; flex-direction: column;">
                <button class="scenario-btn" style="width: 100%; text-align: left; padding: 10px 14px; border-radius: var(--radius-sm);" onclick="focusGroupOfNodes(['${fromNode.id}', '${toNode.id}']);">Chỉ xem hai đầu cạnh</button>
                <button class="scenario-btn" style="width: 100%; text-align: left; padding: 10px 14px; border-radius: var(--radius-sm);" onclick="triggerScenarioAnalysis('${fromNode.id}');"> Phân tích kịch bản từ <strong>${fromNode.label}</strong></button>
            </div>
        `;
    }
    
    popup.classList.remove('hidden');
}

closeBtn.addEventListener('click', () => {
    popup.classList.add('hidden');
});

// Highlight & Hover Logic
let selectedScenarioNode = null;

network.on('click', function (params) {
    // Hide Vonika Sidebar if it is open when interacting with the graph
    if (typeof vonikaSidebar !== 'undefined' && vonikaSidebar) {
        vonikaSidebar.classList.add('collapsed');
    }

    if (params.nodes.length > 0) {
        // Node clicked
        const nodeId = params.nodes[0];
        const nodeData = mockNodes.find(n => n.id === nodeId);
        showPopup('NODE', nodeData);
        highlightConnections(nodeId);
        
        // Setup Scenario UI
        selectedScenarioNode = nodeData;
        document.getElementById('scenario-desc').innerHTML = `Phân tích kịch bản từ: <strong style="color:${colorMap[nodeData.group].highlight}">${nodeData.label}</strong>`;
        document.getElementById('scenario-up-btn').disabled = false;
        document.getElementById('scenario-down-btn').disabled = false;
        document.getElementById('scenario-results').innerHTML = '';
        
    } else if (params.edges.length > 0) {
        // Edge clicked
        const edgeId = params.edges[0];
        const edgeData = mockEdges.find(e => e.id === edgeId);
        showPopup('EDGE', edgeData);
        focusEdge(edgeId);
        resetScenarioUI();
    } else {
        // Clicked on background
        popup.classList.add('hidden');
        resetHighlight();
        resetScenarioUI();
        
        const url = new URL(window.location);
        url.searchParams.delete('node');
        url.searchParams.delete('edge');
        window.history.replaceState({}, '', url);
    }
});

function resetScenarioUI() {
    selectedScenarioNode = null;
    document.getElementById('scenario-desc').innerHTML = `Chọn một node để phân tích.`;
    document.getElementById('scenario-up-btn').disabled = true;
    document.getElementById('scenario-down-btn').disabled = true;
    document.getElementById('scenario-results').innerHTML = '';
}

network.on("hoverEdge", function (e) {
    if (!edges.get(e.edge)) return;
    edges.update({ id: e.edge, font: { color: '#ffffff', size: 12, strokeWidth: 3, strokeColor: '#111111' } });
});
network.on("blurEdge", function (e) {
    const edgeData = edges.get(e.edge);
    if (!edgeData) return;
    if (!edgeData.highlighted) {
        edges.update({ id: e.edge, font: { color: 'transparent', size: 11, strokeWidth: 0 } });
    } else {
        edges.update({ id: e.edge, font: { color: '#e0e0e0', size: 11, strokeWidth: 3, strokeColor: '#111111' } });
    }
});

// Pin node on drag end
network.on("dragEnd", function(params) {
    if (params.nodes.length > 0) {
        nodes.update({id: params.nodes[0], fixed: {x: true, y: true}});
    }
});

// Unpin node on double click
network.on("doubleClick", function(params) {
    if (params.nodes.length > 0) {
        nodes.update({id: params.nodes[0], fixed: {x: false, y: false}});
    }
});

function highlightConnections(selectedNodeId, maxDepth = 1) {
    const connectedNodes = new Set([selectedNodeId]);
    const connectedEdges = new Set();
    
    let currentLevelNodes = new Set([selectedNodeId]);
    
    for (let depth = 0; depth < maxDepth; depth++) {
        let nextLevelNodes = new Set();
        currentLevelNodes.forEach(nId => {
            edges.get().forEach(e => {
                if (e.hidden) return; // Ignore filtered out edges
                if (e.from === nId) {
                    connectedNodes.add(e.to);
                    connectedEdges.add(e.id);
                    nextLevelNodes.add(e.to);
                }
                if (e.to === nId) {
                    connectedNodes.add(e.from);
                    connectedEdges.add(e.id);
                    nextLevelNodes.add(e.from);
                }
            });
        });
        currentLevelNodes = nextLevelNodes;
    }

    // Dim unrelated nodes
    const nodesToUpdate = nodes.get().map(n => {
        const bg = colorMap[n.group].background;
        const bd = colorMap[n.group].border;
        if (connectedNodes.has(n.id)) {
            return { id: n.id, color: { background: bg, border: bd, opacity: 1 }, font: { color: '#e0e0e0' } };
        } else {
            return { id: n.id, color: { background: bg, border: bd, opacity: 0.25 }, font: { color: 'rgba(224,224,224,0.4)' } };
        }
    });
    nodes.update(nodesToUpdate);

    // Dim unrelated edges & show labels for related edges
    const edgesToUpdate = edges.get().map(e => {
        if (connectedEdges.has(e.id)) {
            return { id: e.id, highlighted: true, color: { color: e.originalColor, highlight: e.originalColor, hover: e.originalColor, inherit: false }, font: { color: '#e0e0e0', size: 11, strokeWidth: 3, strokeColor: '#111111' } };
        } else {
            return { id: e.id, highlighted: false, color: { color: 'rgba(128,128,128,0.1)', highlight: 'rgba(128,128,128,0.1)', hover: 'rgba(128,128,128,0.1)', inherit: false }, font: { color: 'transparent', size: 11, strokeWidth: 0 } };
        }
    });
    edges.update(edgesToUpdate);

    // Zoom to fit the connected nodes
    network.fit({
        nodes: Array.from(connectedNodes),
        animation: { duration: 600, easingFunction: 'easeInOutQuad' }
    });
}

function focusEdge(edgeId) {
    const eData = mockEdges.find(e => e.id === edgeId);
    if (!eData) return;

    // Reset selection to prevent vis.js from keeping previous node highlighted
    network.unselectAll();
    network.selectEdges([edgeId]);

    const connectedNodes = new Set([eData.from, eData.to]);
    
    // Dim unrelated nodes
    const nodesToUpdate = nodes.get().map(n => {
        const bg = colorMap[n.group].background;
        const bd = colorMap[n.group].border;
        if (connectedNodes.has(n.id)) {
            return { id: n.id, color: { background: bg, border: bd, opacity: 1 }, font: { color: '#e0e0e0' } };
        } else {
            return { id: n.id, color: { background: bg, border: bd, opacity: 0.25 }, font: { color: 'rgba(224,224,224,0.4)' } };
        }
    });
    nodes.update(nodesToUpdate);

    // Dim unrelated edges
    const edgesToUpdate = edges.get().map(e => {
        if (e.id === edgeId) {
            return { id: e.id, highlighted: true, color: { color: e.originalColor, highlight: e.originalColor, hover: e.originalColor, inherit: false, opacity: 1 }, font: { color: '#e0e0e0', size: 12, strokeWidth: 3, strokeColor: '#111111' } };
        } else {
            return { id: e.id, highlighted: false, color: { color: 'rgba(128,128,128,0.1)', highlight: 'rgba(128,128,128,0.1)', hover: 'rgba(128,128,128,0.1)', inherit: false, opacity: 0.1 }, font: { color: 'transparent', size: 11, strokeWidth: 0 } };
        }
    });
    edges.update(edgesToUpdate);

    // Zoom to fit the connected nodes
    network.fit({
        nodes: Array.from(connectedNodes),
        animation: { duration: 600, easingFunction: 'easeInOutQuad' }
    });
}

function resetHighlight() {
    const nodesToUpdate = nodes.get().map(n => {
        return { id: n.id, color: { background: colorMap[n.group].background, border: colorMap[n.group].border, opacity: 1 }, font: { color: '#e0e0e0' } };
    });
    nodes.update(nodesToUpdate);

    const edgesToUpdate = edges.get().map(e => {
        return { id: e.id, highlighted: false, color: { color: e.originalColor, highlight: e.originalColor, hover: e.originalColor, inherit: false }, font: { color: 'transparent', size: 11, strokeWidth: 0 } };
    });
    edges.update(edgesToUpdate);
}


// Unified Filter Logic
const positiveEdges = GLOBAL_POSITIVE;
const negativeEdges = GLOBAL_NEGATIVE;
const structureEdges = GLOBAL_STRUCTURE;

function applyFilters() {
    // 1. Get filter states
    const activeGroups = Array.from(document.querySelectorAll('.filter-section:first-of-type input:checked')).map(cb => cb.value);
    
    const showCausal = document.getElementById('filter-edge-causal').checked;
    const showStructural = document.getElementById('filter-edge-structural').checked;
    const showPositive = document.getElementById('filter-edge-positive').checked;
    const showNegative = document.getElementById('filter-edge-negative').checked;
    const showOrphan = document.getElementById('filter-orphan').checked;
    
    const activeSources = Array.from(document.querySelectorAll('.source-filter:checked')).map(cb => cb.value);
    
    const visibleEdges = new Set();
    const connectedNodesByVisibleEdges = new Set();
    
    // 2. Filter edges
    const edgesToUpdate = edges.get().map(e => {
        let isStructural = structureEdges.includes(e.label);
        let isPositive = positiveEdges.includes(e.label);
        let isNegative = negativeEdges.includes(e.label);
        
        let passType = (isStructural && showStructural) || (!isStructural && showCausal);
        let passNature = true;
        if (!isStructural) {
             if (isPositive && !showPositive) passNature = false;
             if (isNegative && !showNegative) passNature = false;
        }
        
        let passSource = false;
        if (e.source_files && e.source_files.length > 0) {
            passSource = e.source_files.some(s => activeSources.includes(s));
        } else {
            passSource = true; 
        }
        
        const isVisible = passType && passNature && passSource;
        if (isVisible) {
            visibleEdges.add(e.id);
            connectedNodesByVisibleEdges.add(e.from);
            connectedNodesByVisibleEdges.add(e.to);
        }
        
        return { id: e.id, hidden: !isVisible };
    });
    edges.update(edgesToUpdate);
    
    // 3. Filter nodes
    const nodesToUpdate = nodes.get().map(n => {
        let passGroup = activeGroups.includes(n.group);
        let passOrphan = showOrphan || connectedNodesByVisibleEdges.has(n.id);
        
        let isVisible = passGroup && passOrphan;
        
        const bg = colorMap[n.group].background;
        const bd = colorMap[n.group].border;
        return { id: n.id, hidden: !isVisible, color: { background: bg, border: bd } };
    });
    nodes.update(nodesToUpdate);
}

document.querySelectorAll('.filter-item input').forEach(cb => {
    cb.addEventListener('change', (e) => {
        // Automatically disable/enable child checkboxes when parent is toggled
        if (e.target.id === 'filter-edge-causal') {
            const pos = document.getElementById('filter-edge-positive');
            const neg = document.getElementById('filter-edge-negative');
            pos.disabled = !e.target.checked;
            neg.disabled = !e.target.checked;
        }
        applyFilters();
    });
});

// Run once on load to apply default checkbox states
applyFilters();

// Search Logic with Autocomplete
const searchInput = document.getElementById('searchInput');
const searchBtn = document.getElementById('searchBtn');
const searchDropdown = document.getElementById('search-dropdown');

function removeDiacritics(str) {
    if (!str) return '';
    return String(str).normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/đ/g, 'd').replace(/Đ/g, 'D').toLowerCase();
}

function highlightMatch(text, query) {
    if (!query) return text;
    const lowerText = removeDiacritics(text);
    const index = lowerText.indexOf(query);
    if (index >= 0) {
        return text.substring(0, index) + `<span class="search-highlight">` + text.substring(index, index + query.length) + `</span>` + text.substring(index + query.length);
    }
    return text;
}

function handleSearchInput() {
    const query = removeDiacritics(searchInput.value.trim());
    if (!query) {
        searchDropdown.classList.add('hidden');
        searchDropdown.innerHTML = '';
        return;
    }
    
    // Find matching nodes with scoring
    const matchedNodes = mockNodes.map(n => {
        const labelNorm = removeDiacritics(n.label);
        let score = 0;
        let matchAlias = null;
        
        if (labelNorm === query) score = 100;
        else if (labelNorm.startsWith(query)) score = 80;
        else if (labelNorm.includes(query)) score = 50;
        
        if (score < 100) {
            for (let a of n.aliases) {
                const aNorm = removeDiacritics(a);
                if (aNorm === query) { score = Math.max(score, 90); matchAlias = a; }
                else if (aNorm.startsWith(query)) { score = Math.max(score, 70); matchAlias = a; }
                else if (aNorm.includes(query)) { score = Math.max(score, 40); matchAlias = a; }
            }
        }
        
        return { node: n, score, matchAlias };
    }).filter(item => item.score > 0).sort((a, b) => b.score - a.score || (nodeDegree[b.node.id]||0) - (nodeDegree[a.node.id]||0));
    
    // Find matching edges with scoring
    const matchedEdges = mockEdges.map(e => {
        const relNorm = removeDiacritics(e.relation);
        const lblNorm = removeDiacritics(e.label);
        let score = 0;
        let matchField = null;
        
        if (relNorm.includes(query)) { score = 50; matchField = 'relation'; }
        else if (lblNorm.includes(query)) { score = 40; matchField = 'label'; }
        
        return { edge: e, score, matchField };
    }).filter(item => item.score > 0).sort((a, b) => b.score - a.score);
    
    if (matchedNodes.length === 0 && matchedEdges.length === 0) {
        searchDropdown.innerHTML = '<div style="padding: 12px; color: #888; font-size: 12px; text-align: center;">Không tìm thấy kết quả</div>';
        searchDropdown.classList.remove('hidden');
        return;
    }
    
    let html = '';
    
    if (matchedNodes.length > 0) {
        html += `<div class="search-group-title">Nodes (${matchedNodes.length})</div>`;
        matchedNodes.forEach(item => {
            const n = item.node;
            let labelHtml = highlightMatch(n.label, query);
            let aliasHtml = item.matchAlias ? `<div style="font-size: 11px; color: #888; margin-bottom: 2px;">Bao gồm: ${highlightMatch(item.matchAlias, query)}</div>` : '';
            
            const groupName = n.group === 'TICKER' ? 'Cổ phiếu' : (n.group === 'MACRO' ? 'Vĩ mô' : (n.group === 'COMPANY' ? 'Doanh nghiệp' : 'Sự kiện'));
            
            html += `
            <div class="search-item" onclick="focusNode('${n.id}')">
                <div class="search-item-title">${labelHtml}</div>
                ${aliasHtml}
                <div class="search-item-meta">
                    <span style="color: ${colorMap[n.group].highlight}">${groupName}</span>
                    <span>Liên kết: ${nodeDegree[n.id] || 0}</span>
                </div>
            </div>`;
        });
        if (matchedNodes.length > 1) {
            html += `<div class="search-item" style="text-align: center; color: #4caf50; font-size: 12px;" onclick="focusGroupOfNodes([${matchedNodes.map(item => `'${item.node.id}'`).join(',')}])">Chọn tất cả ${matchedNodes.length} node khớp</div>`;
        }
    }
    
    if (matchedEdges.length > 0) {
        html += `<div class="search-group-title">Quan hệ (${matchedEdges.length})</div>`;
        matchedEdges.forEach(item => {
            const e = item.edge;
            const fromNode = mockNodes.find(n => n.id === e.from).label;
            const toNode = mockNodes.find(n => n.id === e.to).label;
            
            let relHtml = item.matchField === 'relation' ? highlightMatch(e.relation, query) : e.relation;
            let lblHtml = item.matchField === 'label' ? highlightMatch(e.label, query) : e.label;
            
            html += `
            <div class="search-item" onclick="focusEdge('${e.id}')">
                <div class="search-item-title">${relHtml} (${lblHtml})</div>
                <div class="search-item-meta">
                    <span>${fromNode} → ${toNode}</span>
                </div>
            </div>`;
        });
    }
    
    searchDropdown.innerHTML = html;
    searchDropdown.classList.remove('hidden');
}

function focusNode(id) {
    searchDropdown.classList.add('hidden');
    searchInput.value = '';
    network.focus(id, { scale: 1.5, animation: { duration: 1000, easingFunction: 'easeInOutQuad' } });
    network.selectNodes([id]);
    const node = mockNodes.find(n => n.id === id);
    showPopup('NODE', node);
}

function focusGroupOfNodes(ids) {
    searchDropdown.classList.add('hidden');
    searchInput.value = '';
    network.selectNodes(ids);
    network.fit({ nodes: ids, animation: { duration: 1000, easingFunction: 'easeInOutQuad' } });
}

searchInput.addEventListener('input', handleSearchInput);
searchInput.addEventListener('focus', () => {
    if(searchInput.value.trim() === '') {
        let topNodes = [...mockNodes].sort((a,b) => (nodeDegree[b.id]||0) - (nodeDegree[a.id]||0)).slice(0, 5);
        let html = `<div class="search-group-title">Gợi ý bắt đầu</div>`;
        topNodes.forEach(n => {
            const groupName = n.group === 'TICKER' ? 'Cổ phiếu' : (n.group === 'MACRO' ? 'Vĩ mô' : (n.group === 'COMPANY' ? 'Doanh nghiệp' : 'Sự kiện'));
            html += `
            <div class="search-item" onclick="focusNode('${n.id}')">
                <div class="search-item-title">${n.label}</div>
                <div class="search-item-meta">
                    <span style="color: ${colorMap[n.group].highlight}">${groupName}</span>
                    <span>Liên kết: ${nodeDegree[n.id] || 0}</span>
                </div>
            </div>`;
        });
        searchDropdown.innerHTML = html;
        searchDropdown.classList.remove('hidden');
    } else {
        handleSearchInput();
    }
});

// Close dropdown on click outside
document.addEventListener('click', (e) => {
    if(!e.target.closest('.search-box')) {
        searchDropdown.classList.add('hidden');
    }
});

// Focus multiple nodes
window.focusGroupOfNodes = function(nodeIds) {
    searchDropdown.classList.add('hidden');
    searchInput.value = '';
    
    network.unselectAll();
    network.selectNodes(nodeIds);
    
    const connectedNodes = new Set(nodeIds);
    const connectedEdges = new Set();
    
    // Collect all immediate neighbors and connected edges
    nodeIds.forEach(nId => {
        edges.get().forEach(e => {
            if (e.hidden) return;
            if (e.from === nId) {
                connectedNodes.add(e.to);
                connectedEdges.add(e.id);
            }
            if (e.to === nId) {
                connectedNodes.add(e.from);
                connectedEdges.add(e.id);
            }
        });
    });
    
    // Zoom map to fit core nodes
    network.fit({
        nodes: nodeIds,
        animation: { duration: 600, easingFunction: 'easeInOutQuad' }
    });
    
    // Highlight these nodes and dim the rest
    const nodesToUpdate = nodes.get().map(n => {
        const bg = colorMap[n.group].background;
        const bd = colorMap[n.group].border;
        if (connectedNodes.has(n.id)) {
            return { id: n.id, color: { background: bg, border: bd, opacity: 1 }, font: { color: '#e0e0e0' } };
        } else {
            return { id: n.id, color: { background: bg, border: bd, opacity: 0.25 }, font: { color: 'rgba(224,224,224,0.4)' } };
        }
    });
    nodes.update(nodesToUpdate);
    
    // Highlight all connected edges
    const edgesToUpdate = edges.get().map(e => {
        if (connectedEdges.has(e.id)) {
            return { id: e.id, highlighted: true, color: { color: e.originalColor, highlight: e.originalColor, hover: e.originalColor, inherit: false }, font: { color: '#e0e0e0', size: 11, strokeWidth: 3, strokeColor: '#111111' } };
        }
        return { id: e.id, highlighted: false, color: { color: 'rgba(128,128,128,0.1)', highlight: 'rgba(128,128,128,0.1)', hover: 'rgba(128,128,128,0.1)', inherit: false }, font: { color: 'transparent', size: 11, strokeWidth: 0 } };
    });
    edges.update(edgesToUpdate);
};

window.triggerScenarioAnalysis = function(nodeId) {
    // Trigger node selection and scenario logic
    network.selectNodes([nodeId]);
    network.emit('click', {nodes: [nodeId], edges: []});
    
    // Open sidebar if closed
    const controlPanel = document.getElementById('controlPanel');
    if (controlPanel && controlPanel.classList.contains('collapsed')) {
        controlPanel.classList.remove('collapsed');
        document.body.classList.remove('sidebar-collapsed');
    }
    
    // Open scenario details panel
    const scenarioSection = document.querySelector('.scenario-section');
    if (scenarioSection && !scenarioSection.hasAttribute('open')) {
        scenarioSection.setAttribute('open', '');
    }
};

// URL State Initialization
window.addEventListener('DOMContentLoaded', () => {
    const urlParams = new URLSearchParams(window.location.search);
    const startNode = urlParams.get('node');
    const startEdge = urlParams.get('edge');

    if (startNode) {
        setTimeout(() => {
            network.selectNodes([startNode]);
            focusNode(startNode);
        }, 800);
    } else if (startEdge) {
        setTimeout(() => {
            network.selectEdges([startEdge]);
            focusEdge(startEdge);
        }, 800);
    }
});
const sidebarToggleBtn = document.getElementById('sidebarToggle');
const controlPanel = document.getElementById('controlPanel');

sidebarToggleBtn.addEventListener('click', () => {
    controlPanel.classList.toggle('collapsed');
    document.body.classList.toggle('sidebar-collapsed');
});

// Calculate and render sidebar counts
function updateSidebarCounts() {
    const nodeCounts = { TICKER: 0, MACRO: 0, EVENT: 0, COMPANY: 0 };
    mockNodes.forEach(n => nodeCounts[n.group] = (nodeCounts[n.group] || 0) + 1);
    
    let causalCount = 0, structuralCount = 0;
    let posCount = 0, negCount = 0;
    const sourceCounts = {};
    
    const posEdges = GLOBAL_POSITIVE;
    const negEdges = GLOBAL_NEGATIVE;
    const structEdges = GLOBAL_STRUCTURE;
    
    mockEdges.forEach(e => {
        let isStruct = structEdges.includes(e.label);
        if (isStruct) structuralCount++; else causalCount++;
        
        if (posEdges.includes(e.label)) posCount++;
        if (negEdges.includes(e.label)) negCount++;
        
        if (e.source_files) {
            e.source_files.forEach(s => {
                sourceCounts[s] = (sourceCounts[s] || 0) + 1;
            });
        }
    });

    // Update Node Types
    document.querySelectorAll('.filter-section:first-of-type .filter-item').forEach(label => {
        const input = label.querySelector('input');
        const textNode = Array.from(label.childNodes).find(n => n.nodeType === 3 && n.textContent.trim().length > 0);
        if (input && textNode) {
            const baseText = textNode.textContent.replace(/\(\d+\)/, '').trim();
            textNode.textContent = ` ${baseText} (${nodeCounts[input.value] || 0})`;
        }
    });
    
    // Update Edge Types
    const edgeTypesMap = {
        'filter-edge-causal': causalCount,
        'filter-edge-structural': structuralCount,
        'filter-edge-positive': posCount,
        'filter-edge-negative': negCount
    };
    
    Object.keys(edgeTypesMap).forEach(id => {
        const input = document.getElementById(id);
        if (input) {
            const label = input.closest('.filter-item');
            const textNode = Array.from(label.childNodes).find(n => n.nodeType === 3 && n.textContent.trim().length > 0);
            if (textNode) {
                const baseText = textNode.textContent.replace(/\(\d+\)/, '').trim();
                textNode.textContent = ` ${baseText} (${edgeTypesMap[id]})`;
            }
        }
    });
    
    // Update Sources
    document.querySelectorAll('#source-filters .filter-item').forEach(label => {
        const input = label.querySelector('input');
        const textNode = Array.from(label.childNodes).find(n => n.nodeType === 3 && n.textContent.trim().length > 0);
        if (input && textNode) {
            const baseText = textNode.textContent.replace(/\(\d+\)/, '').trim();
            textNode.textContent = ` ${baseText} (${sourceCounts[input.value] || 0})`;
        }
    });
}
updateSidebarCounts();

// Scenario Propagation Logic
document.getElementById('scenario-up-btn').addEventListener('click', () => runScenario(1));
document.getElementById('scenario-down-btn').addEventListener('click', () => runScenario(-1));

function runScenario(shockSign) {
    if (!selectedScenarioNode) return;
    
    resetHighlight();
    
    let scores = {};
    let depths = {}; // Track shortest path depth
    scores[selectedScenarioNode.id] = shockSign;
    depths[selectedScenarioNode.id] = 0;
    
    const positiveEdges = ['Thúc đẩy', 'Hưởng lợi', 'Tác động tích cực', 'Tích cực'];
    const negativeEdges = ['Gây áp lực', 'Tác động tiêu cực', 'Tiêu cực'];
    const structureEdges = ['Bao gồm', 'Công ty mẹ', 'Cấu trúc'];
    
    let connectedNodes = new Set([selectedScenarioNode.id]);
    let connectedEdges = new Set();
    
    // Queue for BFS: {id, score, depth}
    let queue = [{ id: selectedScenarioNode.id, score: shockSign, depth: 0 }];
    
    while(queue.length > 0) {
        let current = queue.shift();
        if (current.depth >= 4) continue; // Max depth 4
        
        mockEdges.forEach(e => {
            if (e.from === current.id) {
                let edgeSign = 0;
                if (positiveEdges.includes(e.label)) edgeSign = 1;
                else if (negativeEdges.includes(e.label)) edgeSign = -1;
                else if (structureEdges.includes(e.label)) edgeSign = 1; 
                
                if (edgeSign !== 0) {
                    let impact = current.score * edgeSign * 0.85; 
                    
                    if (Math.abs(impact) > 0.05) {
                        scores[e.to] = (scores[e.to] || 0) + impact;
                        
                        let nextDepth = current.depth + 1;
                        if (!depths[e.to] || nextDepth < depths[e.to]) {
                            depths[e.to] = nextDepth;
                        }
                        
                        connectedNodes.add(e.to);
                        connectedEdges.add(e.id);
                        queue.push({ id: e.to, score: impact, depth: nextDepth });
                    }
                }
            }
        });
    }
    
    // Render graph with scenario colors
    const nodesToUpdate = nodes.get().map(n => {
        if (connectedNodes.has(n.id)) {
            let s = scores[n.id] || 0;
            let hlBg = colorMap[n.group].highlight;
            let hlBorder = colorMap[n.group].border;
            
            // Color affected nodes based on final net score and entity type
            if (n.id !== selectedScenarioNode.id && Math.abs(s) > 0.1) {
                const isIndustryOrTicker = n.group === 'TICKER' || n.group === 'COMPANY' || n.label.toLowerCase().startsWith('ngành');
                if (s > 0) { 
                    hlBg = isIndustryOrTicker ? '#4caf50' : '#3b82f6'; 
                    hlBorder = isIndustryOrTicker ? '#2e7d32' : '#1d4ed8'; 
                } else if (s < 0) { 
                    hlBg = isIndustryOrTicker ? '#f44336' : '#f97316'; 
                    hlBorder = isIndustryOrTicker ? '#c62828' : '#c2410c'; 
                }
            }
            return { id: n.id, color: { background: hlBg, border: hlBorder, opacity: 1 }, font: { color: '#ffffff' } };
        } else {
            return { id: n.id, color: { background: colorMap[n.group].background, opacity: 0.15 }, font: { color: 'rgba(224,224,224,0.15)' } };
        }
    });
    nodes.update(nodesToUpdate);
    
    const edgesToUpdate = edges.get().map(e => {
        if (connectedEdges.has(e.id)) {
            return { id: e.id, highlighted: true, color: { color: e.originalColor, opacity: 1, inherit: false }, font: { color: '#e0e0e0', size: 11, strokeWidth: 3, strokeColor: '#111111' } };
        } else {
            return { id: e.id, highlighted: false, color: { color: e.originalColor, opacity: 0.1, inherit: false }, font: { color: 'transparent', size: 11, strokeWidth: 0 } };
        }
    });
    edges.update(edgesToUpdate);
    
    network.fit({ nodes: Array.from(connectedNodes), animation: { duration: 600, easingFunction: 'easeInOutQuad' } });
    
    // Render sidebar results
    const resultsContainer = document.getElementById('scenario-results');
    const affected = Object.keys(scores).filter(id => id != selectedScenarioNode.id);
    
    if (affected.length === 0) {
        resultsContainer.innerHTML = '<span style="color:#888;">Không có tác động lan truyền.</span>';
        return;
    }
    
    // Sort by absolute impact
    affected.sort((a, b) => Math.abs(scores[b]) - Math.abs(scores[a]));
    
    let html = `<p style="font-weight: 600; margin-bottom: 4px; border-bottom: 1px solid var(--panel-border); padding-bottom: 8px;">Dự báo mức độ ảnh hưởng:</p>`;
    affected.forEach(id => {
        let n = mockNodes.find(node => node.id === id);
        let s = scores[id];
        let stepText = depths[id] ? `(Qua ${depths[id]} bước)` : '';
        
        let color = '#94a3b8';
        let text = 'Trái chiều / Triệt tiêu';
        
        if (Math.abs(s) >= 0.15) {
            if (n.group === 'TICKER' || n.group === 'COMPANY') {
                color = s > 0 ? '#4caf50' : '#f44336';
                text = s > 0 ? 'Tích cực' : 'Tiêu cực';
            } else if (n.label.toLowerCase().startsWith('ngành')) {
                color = s > 0 ? '#4caf50' : '#f44336';
                text = s > 0 ? 'Thuận lợi' : 'Khó khăn';
            } else {
                color = s > 0 ? '#3b82f6' : '#f97316';
                text = s > 0 ? 'Tăng ▲' : 'Giảm ▼';
            }
        }
        
        html += `
        <div style="background: #111111; padding: 10px; border-radius: 6px; border-left: 3px solid ${color}; display: flex; justify-content: space-between; align-items: center; cursor: pointer; margin-bottom: 8px;" onclick="network.selectNodes(['${id}']); network.emit('click', {nodes: ['${id}'], edges: []})">
            <div>
                <div style="font-weight:600; font-size: 13px; color: ${colorMap[n.group].highlight}">${n.label}</div>
                <div style="font-size: 11px; color: var(--text-muted); margin-top: 2px;">${n.group === 'TICKER' ? 'Cổ phiếu' : 'Yếu tố'} ${stepText}</div>
            </div>
            <div style="color:${color}; font-weight: 500; font-size: 13px;">${text}</div>
        </div>`;
    });
    resultsContainer.innerHTML = html;
}

// Load data at startup
loadGraphData();

// Vonika Sidebar
const vonikaSidebar = document.getElementById('vonika-sidebar');
const vonikaToggleBtn = document.getElementById('vonika-toggle-btn');
const vonikaCloseBtn = document.getElementById('vonika-close-btn');
const vonikaContextBox = document.getElementById('vonika-context');
const vonikaContextText = document.getElementById('vonika-context-text');

let currentVonikaContext = null;

if (vonikaToggleBtn && vonikaCloseBtn && vonikaSidebar) {
    vonikaToggleBtn.addEventListener('click', () => {
        vonikaSidebar.classList.remove('collapsed');
    });

    vonikaCloseBtn.addEventListener('click', () => {
        vonikaSidebar.classList.add('collapsed');
    });
}

window.askVonika = function(type, id) {
    if (vonikaSidebar) {
        vonikaSidebar.classList.remove('collapsed');
    }
    
    // Set Context
    if (type === 'NODE') {
        const node = mockNodes.find(n => n.id === id);
        if (node && vonikaContextText && vonikaContextBox) {
            currentVonikaContext = { type: 'NODE', data: node };
            vonikaContextText.innerHTML = `Node: <strong>${node.label}</strong>`;
            vonikaContextBox.classList.remove('hidden');
        }
    } else if (type === 'EDGE') {
        const edge = mockEdges.find(e => e.id === id);
        if (edge && vonikaContextText && vonikaContextBox) {
            const fromNode = mockNodes.find(n => n.id === edge.from);
            const toNode = mockNodes.find(n => n.id === edge.to);
            currentVonikaContext = { type: 'EDGE', data: edge, from: fromNode, to: toNode };
            vonikaContextText.innerHTML = `Liên kết: <strong>${fromNode.label}</strong> ➔ <strong>${toNode.label}</strong>`;
            vonikaContextBox.classList.remove('hidden');
        }
    }
};

window.clearVonikaContext = function() {
    currentVonikaContext = null;
    if (vonikaContextBox) {
        vonikaContextBox.classList.add('hidden');
    }
};

document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible' && network) {
        setTimeout(() => {
            network.fit({ animation: { duration: 800, easingFunction: 'easeInOutQuad' } });
        }, 100);
    }
});

// Export Graph to Markdown
window.exportGraphToMarkdown = function() {
    let md = "# Tổng hợp Nội dung Đồ thị Tri thức (Fintech KG)\n\n";
    md += `*Thời gian xuất: ${new Date().toLocaleString('vi-VN')}*\n\n`;
    
    md += "## 1. Danh sách Thực thể (Nodes)\n\n";
    const groups = { TICKER: 'Mã Chứng Khoán', MACRO: 'Vĩ Mô', EVENT: 'Sự Kiện', COMPANY: 'Doanh Nghiệp' };
    
    Object.keys(groups).forEach(gKey => {
        const groupNodes = mockNodes.filter(n => n.group === gKey);
        if (groupNodes.length > 0) {
            md += `### ${groups[gKey]}\n`;
            groupNodes.forEach(n => {
                md += `- **${n.label}**`;
                if (n.aliases && n.aliases.length) {
                    md += ` *(Tên khác: ${n.aliases.join(', ')})*`;
                }
                md += `\n`;
            });
            md += "\n";
        }
    });

    md += "## 2. Danh sách Mối quan hệ (Edges)\n\n";
    mockEdges.forEach(e => {
        const fromNode = mockNodes.find(n => n.id === e.from);
        const toNode = mockNodes.find(n => n.id === e.to);
        if (fromNode && toNode) {
            md += `- **${fromNode.label}** ➔ [${e.label}] ➔ **${toNode.label}**\n`;
            if (e.relation) md += `  - *Bản chất:* ${e.relation}\n`;
            if (e.evidence) md += `  - *Trích dẫn:* "${e.evidence}"\n`;
            if (e.source_files && e.source_files.length) md += `  - *Nguồn:* ${e.source_files.join(', ')}\n`;
            md += "\n";
        }
    });

    // Generate file and trigger download
    const blob = new Blob([md], { type: 'text/markdown;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `FintechKG_Export_${new Date().toISOString().slice(0,10)}.md`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
};

// VONIKA CHAT UI LOGIC
const vonikaInput = document.getElementById('vonika-input');
const vonikaSendBtn = document.getElementById('vonika-send-btn');
const vonikaChatHistory = document.getElementById('vonika-chat-history');

let currentChatId = null;

function collectSourceFiles(ctx) {
    if (ctx && ctx.type === 'EDGE') return ctx.data.source_files || [];
    return [];
}

function buildGraphContext(ctx) {
    if (!ctx) return null;
    if (ctx.type === 'EDGE') {
        const e = ctx.data;
        return {
            type: 'EDGE',
            source: ctx.from?.label,
            target: ctx.to?.label,
            label: e.label,
            relation: e.relation,
            evidence: e.evidence,
            source_files: e.source_files || []
        };
    }
    const n = ctx.data;
    const relations = mockEdges
        .filter(e => e.from === n.id || e.to === n.id)
        .map(e => ({
            source: mockNodes.find(x => x.id === e.from)?.label,
            target: mockNodes.find(x => x.id === e.to)?.label,
            label: e.label,
            relation: e.relation,
            evidence: e.evidence
        }));
    return { type: 'NODE', name: n.label, node_type: n.group, aliases: n.aliases || [], relations };
}

function escapeHtml(s) {
    return String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

function appendMessage(role, text, isHtml = false) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `chat-msg ${role}`;
    if (isHtml) msgDiv.innerHTML = text;
    else msgDiv.textContent = text;
    vonikaChatHistory.appendChild(msgDiv);
    vonikaChatHistory.scrollTop = vonikaChatHistory.scrollHeight;
    return msgDiv;
}

async function handleSend() {
    const text = vonikaInput.value.trim();
    if (!text) return;

    appendMessage('user', text);

    vonikaInput.disabled = true;
    vonikaSendBtn.disabled = true;
    vonikaInput.value = '';
    vonikaInput.style.height = 'auto';

    const loadingMsg = appendMessage(
        'bot',
        '<i class="fa-solid fa-circle-notch fa-spin"></i> Đang phân tích đồ thị...',
        true
    );

    try {
        const { data: insertedData, error: dbError } = await supabaseClient
            .from("chat_messages")
            .insert([{ role: "user", content: text, source: "graph", chat_title: "[GRAPH] Session" }])
            .select();

        if (dbError) throw dbError;
        if (insertedData?.length > 0) currentChatId = insertedData[0].id;

        const payload = {
            query: text,
            context: buildGraphContext(currentVonikaContext),
            source_files: collectSourceFiles(currentVonikaContext),
            chatId: currentChatId
        };

        const res = await fetch(`${backend_url}/graph-chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (!res.ok) throw new Error(`Backend trả về lỗi ${res.status}`);

        const data = await res.json();
        const answer = data.answer || '';

        loadingMsg.remove();
        const rendered = window.marked ? marked.parse(answer) : escapeHtml(answer);
        const safeHtml = window.DOMPurify ? DOMPurify.sanitize(rendered) : rendered;
        appendMessage('bot', `<div class="markdown-body" style="background:transparent;">${safeHtml}</div>`, true);

        const { error: saveError } = await supabaseClient
            .from("chat_messages")
            .insert([{ role: "assistant", content: answer, source: "graph", chat_title: "[GRAPH] Session" }]);
        if (saveError) console.error("Không lưu được tin nhắn bot:", saveError);

    } catch (err) {
        console.error(err);
        loadingMsg.remove();
        appendMessage(
            'bot',
            `<span style="color:#f44336;"><i class="fa-solid fa-circle-exclamation"></i> ${escapeHtml(err.message || 'Không thể kết nối với Vonika Backend!')}</span>`,
            true
        );
    } finally {
        vonikaInput.disabled = false;
        vonikaSendBtn.disabled = false;
        vonikaInput.focus();
    }
}

if (vonikaSendBtn && vonikaInput) {
    vonikaSendBtn.addEventListener('click', handleSend);
    
    vonikaInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    });
    
    vonikaInput.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = (this.scrollHeight) + 'px';
        if(this.scrollHeight > 150) {
            this.style.overflowY = 'auto';
            this.style.height = '150px';
        } else {
            this.style.overflowY = 'hidden';
        }
    });
}
