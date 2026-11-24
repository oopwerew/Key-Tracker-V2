/* ===================================================
   Key Tracker V2 — Client Logic (Vanilla JS)
   =================================================== */

let currentUser = null;
let currentFilter = 'all';
let currentSearch = '';
let searchTimeout = null;

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
  checkAuth();
});

// ==========================================
//           АВТОРИЗАЦИЯ И СЕССИЯ
// ==========================================

async function checkAuth() {
  const token = localStorage.getItem('token');
  if (!token) {
    showAuthScreen();
    return;
  }

  try {
    const res = await fetch('/api/auth/me', {
      headers: { 'Authorization': `Bearer ${token}` }
    });

    if (res.ok) {
      currentUser = await res.json();
      showAppScreen();
    } else {
      localStorage.removeItem('token');
      showAuthScreen();
    }
  } catch (err) {
    console.error('Ошибка проверки сессии:', err);
    showAuthScreen();
  }
}

function showAuthScreen() {
  document.getElementById('authScreen').style.display = 'flex';
  document.getElementById('appScreen').style.display = 'none';
  clearAuthAlert();
}

function showAppScreen() {
  document.getElementById('authScreen').style.display = 'none';
  document.getElementById('appScreen').style.display = 'block';

  // Установка данных пользователя в шапку
  document.getElementById('userNameDisplay').textContent = currentUser.full_name;
  
  const roleBadge = document.getElementById('userRoleBadge');
  if (currentUser.role === 'admin') {
    roleBadge.textContent = 'Администратор';
    roleBadge.className = 'role-badge admin';
    document.getElementById('adminActionButtons').style.display = 'flex';
  } else {
    roleBadge.textContent = 'Пользователь';
    roleBadge.className = 'role-badge user';
    document.getElementById('adminActionButtons').style.display = 'none';
  }

  loadStats();
  loadRooms();
}

function switchAuthTab(tab) {
  clearAuthAlert();
  const tabLogin = document.getElementById('tabLogin');
  const tabRegister = document.getElementById('tabRegister');
  const loginForm = document.getElementById('loginForm');
  const registerForm = document.getElementById('registerForm');

  if (tab === 'login') {
    tabLogin.classList.add('active');
    tabRegister.classList.remove('active');
    loginForm.style.display = 'block';
    registerForm.style.display = 'none';
  } else {
    tabRegister.classList.add('active');
    tabLogin.classList.remove('active');
    registerForm.style.display = 'block';
    loginForm.style.display = 'none';
  }
}

function toggleAdminInviteField() {
  const isAdmin = document.getElementById('roleAdmin').checked;
  const inviteGroup = document.getElementById('adminInviteGroup');
  inviteGroup.style.display = isAdmin ? 'block' : 'none';
  const inviteInput = document.getElementById('regInviteCode');
  inviteInput.required = isAdmin;
}

function showAuthAlert(message, type = 'error') {
  const alert = document.getElementById('authAlert');
  alert.className = `alert-box ${type}`;
  alert.textContent = message;
  alert.style.display = 'block';
}

function clearAuthAlert() {
  const alert = document.getElementById('authAlert');
  alert.style.display = 'none';
  alert.textContent = '';
}

async function handleLogin(e) {
  e.preventDefault();
  clearAuthAlert();

  const username = document.getElementById('loginUsername').value.trim();
  const password = document.getElementById('loginPassword').value;

  try {
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });

    const data = await res.json();
    if (res.ok) {
      localStorage.setItem('token', data.token);
      currentUser = data.user;
      showAppScreen();
    } else {
      showAuthAlert(data.detail || 'Ошибка авторизации');
    }
  } catch (err) {
    showAuthAlert('Не удалось связаться с сервером');
  }
}

async function handleRegister(e) {
  e.preventDefault();
  clearAuthAlert();

  const full_name = document.getElementById('regFullName').value.trim();
  const username = document.getElementById('regUsername').value.trim();
  const password = document.getElementById('regPassword').value;
  const role = document.querySelector('input[name="accountRole"]:checked').value;
  const invite_code = document.getElementById('regInviteCode').value.trim();

  try {
    const res = await fetch('/api/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ full_name, username, password, role, invite_code })
    });

    const data = await res.json();
    if (res.ok) {
      localStorage.setItem('token', data.token);
      currentUser = data.user;
      showAppScreen();
    } else {
      showAuthAlert(data.detail || 'Ошибка при регистрации');
    }
  } catch (err) {
    showAuthAlert('Не удалось связаться с сервером');
  }
}

async function handleLogout() {
  try {
    await fetch('/api/auth/logout', { method: 'POST' });
  } catch (e) {}
  localStorage.removeItem('token');
  currentUser = null;
  showAuthScreen();
}


// ==========================================
//          ЗАГРУЗКА И ОТОБРАЖЕНИЕ ДАННЫХ
// ==========================================

async function loadStats() {
  try {
    const res = await fetchWithAuth('/api/stats');
    if (res.ok) {
      const stats = await res.json();
      document.getElementById('statTotal').textContent = stats.total;
      document.getElementById('statAvailable').textContent = stats.available;
      document.getElementById('statTaken').textContent = stats.taken;
    }
  } catch (err) {
    console.error('Ошибка загрузки статистики:', err);
  }
}

async function loadRooms() {
  const container = document.getElementById('roomsListContainer');
  
  try {
    const url = `/api/keys?search=${encodeURIComponent(currentSearch)}&status=${encodeURIComponent(currentFilter)}`;
    const res = await fetchWithAuth(url);
    if (!res.ok) return;

    const keys = await res.json();
    container.innerHTML = '';

    if (keys.length === 0) {
      container.innerHTML = `
        <div class="empty-state">
          <span class="icon"><svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg></span>
          <h3>Кабинеты не найдены</h3>
          <p>Попробуйте изменить поисковый запрос или фильтр</p>
        </div>
      `;
      return;
    }

    keys.forEach(key => {
      const row = createRoomRowElement(key);
      container.appendChild(row);
    });
  } catch (err) {
    console.error('Ошибка загрузки кабинетов:', err);
  }
}

function createRoomRowElement(key) {
  const row = document.createElement('div');
  row.className = 'room-row';

  const isAvailable = key.status === 'available';
  const isAdmin = currentUser && currentUser.role === 'admin';
  const isMyKey = !isAvailable && currentUser && (key.taken_by === currentUser.full_name || key.taken_by === currentUser.username);

  // 1. Колонка информации
  const colInfo = document.createElement('div');
  colInfo.className = 'col-info';
  colInfo.innerHTML = `
    <div class="room-badge">№${escapeHtml(key.id)}</div>
    <div class="room-details">
      <div class="room-name">${escapeHtml(key.name)}</div>
      <div class="room-sub">Этаж ${escapeHtml(String(key.floor))}${key.notes ? '  •  ' + escapeHtml(key.notes) : ''}</div>
    </div>
  `;

  // 2. Колонка статуса
  const colStatus = document.createElement('div');
  colStatus.className = 'col-status';

  if (isAvailable) {
    colStatus.innerHTML = `
      <span class="status-badge available">
        <span class="status-dot"></span>
        В наличии
      </span>
    `;
  } else {
    colStatus.innerHTML = `
      <span class="status-badge taken">
        <span class="status-dot"></span>
        На руках
      </span>
      ${isMyKey ? '<span class="status-badge my-key">У вас</span>' : ''}
      <span class="taken-details">
        <span class="taken-name">${escapeHtml(key.taken_by || 'Не указан')}</span>
        ${key.taken_at ? '<span class="taken-date"> (с ' + escapeHtml(key.taken_at) + ')</span>' : ''}
        ${key.phone ? '<span class="taken-date"> • ' + escapeHtml(key.phone) + '</span>' : ''}
        ${key.expected_return ? '<span class="taken-date" style="color: var(--warning-text); font-weight: 500;"> • До: ' + escapeHtml(key.expected_return) + '</span>' : ''}
      </span>
    `;
  }

  // 3. Колонка действий
  const colActions = document.createElement('div');
  colActions.className = 'col-actions';

  if (isAdmin) {
    if (isAvailable) {
      colActions.innerHTML = `
        <button class="btn btn-primary btn-action" onclick="openIssueModal('${escapeHtml(key.id)}', '${escapeHtml(key.name)}')">
          Выдать
        </button>
        <button class="btn-delete" title="Удалить кабинет" onclick="openDeleteModal('${escapeHtml(key.id)}', '${escapeHtml(key.name)}')">
          <span class="icon"><svg viewBox="0 0 24 24"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg></span>
        </button>
      `;
    } else {
      colActions.innerHTML = `
        <button class="btn btn-success btn-action" onclick="returnKey('${escapeHtml(key.id)}')">
          Принять возврат
        </button>
        <button class="btn-delete" title="Удалить кабинет" onclick="openDeleteModal('${escapeHtml(key.id)}', '${escapeHtml(key.name)}')">
          <span class="icon"><svg viewBox="0 0 24 24"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg></span>
        </button>
      `;
    }
  } else {
    // Для обычного пользователя действия скрыты согласно ТЗ
    colActions.innerHTML = '';
  }

  row.appendChild(colInfo);
  row.appendChild(colStatus);
  row.appendChild(colActions);

  return row;
}

// Фильтры и поиск
function setFilter(filter) {
  currentFilter = filter;
  ['filterAll', 'filterAvailable', 'filterTaken'].forEach(id => {
    document.getElementById(id).classList.remove('active');
  });
  if (filter === 'all') document.getElementById('filterAll').classList.add('active');
  if (filter === 'available') document.getElementById('filterAvailable').classList.add('active');
  if (filter === 'taken') document.getElementById('filterTaken').classList.add('active');

  loadRooms();
}

function handleSearch() {
  clearTimeout(searchTimeout);
  searchTimeout = setTimeout(() => {
    currentSearch = document.getElementById('searchInput').value.trim();
    loadRooms();
  }, 200);
}


// ==========================================
//          МОДАЛЬНЫЕ ОКНА И ДЕЙСТВИЯ
// ==========================================

function openModal(id) {
  document.getElementById(id).classList.add('active');
}

function closeModal(id) {
  document.getElementById(id).classList.remove('active');
}

// Выдача ключа
function openIssueModal(keyId, keyName) {
  document.getElementById('issueKeyId').value = keyId;
  document.getElementById('issueModalTitle').textContent = `Выдача ключа №${keyId} (${keyName})`;
  document.getElementById('issueRecipientName').value = '';
  openModal('issueModal');
}

async function submitIssueKey(e) {
  e.preventDefault();
  const keyId = document.getElementById('issueKeyId').value;
  const recipientName = document.getElementById('issueRecipientName').value.trim();

  try {
    const res = await fetchWithAuth(`/api/keys/${keyId}/issue`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ recipient_name: recipientName })
    });

    const data = await res.json();
    if (res.ok) {
      closeModal('issueModal');
      loadStats();
      loadRooms();
    } else {
      alert(data.detail || 'Ошибка выдачи');
    }
  } catch (err) {
    alert('Не удалось отправить запрос');
  }
}

// Возврат ключа
async function returnKey(keyId) {
  try {
    const res = await fetchWithAuth(`/api/keys/${keyId}/return`, {
      method: 'POST'
    });
    const data = await res.json();
    if (res.ok) {
      loadStats();
      loadRooms();
    } else {
      alert(data.detail || 'Ошибка возврата');
    }
  } catch (err) {
    alert('Не удалось отправить запрос');
  }
}

// Добавление кабинета
function openAddKeyModal() {
  document.getElementById('addKeyId').value = '';
  document.getElementById('addKeyName').value = '';
  document.getElementById('addKeyFloor').value = '1';
  document.getElementById('addKeyNotes').value = '';
  openModal('addKeyModal');
}

async function submitAddKey(e) {
  e.preventDefault();
  const id = document.getElementById('addKeyId').value.trim();
  const name = document.getElementById('addKeyName').value.trim();
  const floor = parseInt(document.getElementById('addKeyFloor').value) || 1;
  const notes = document.getElementById('addKeyNotes').value.trim();

  try {
    const res = await fetchWithAuth('/api/keys', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id, name, floor, notes })
    });

    const data = await res.json();
    if (res.ok) {
      closeModal('addKeyModal');
      loadStats();
      loadRooms();
    } else {
      alert(data.detail || 'Ошибка добавления кабинета');
    }
  } catch (err) {
    alert('Не удалось отправить запрос');
  }
}

// Удаление кабинета
function openDeleteModal(keyId, keyName) {
  document.getElementById('deleteKeyId').value = keyId;
  document.getElementById('deleteModalText').textContent = `Вы действительно хотите удалить кабинет №${keyId} (${keyName}) из системы?`;
  openModal('deleteModal');
}

async function confirmDeleteKey() {
  const keyId = document.getElementById('deleteKeyId').value;
  try {
    const res = await fetchWithAuth(`/api/keys/${keyId}`, {
      method: 'DELETE'
    });
    const data = await res.json();
    if (res.ok) {
      closeModal('deleteModal');
      loadStats();
      loadRooms();
    } else {
      alert(data.detail || 'Ошибка удаления');
    }
  } catch (err) {
    alert('Не удалось отправить запрос');
  }
}

// Журнал операций
async function openHistoryModal() {
  const tbody = document.getElementById('historyTableBody');
  tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: var(--text-muted); padding: 20px;">Загрузка...</td></tr>';
  openModal('historyModal');

  try {
    const res = await fetchWithAuth('/api/history');
    if (!res.ok) {
      tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: var(--danger); padding: 20px;">Доступ запрещён</td></tr>';
      return;
    }

    const history = await res.json();
    tbody.innerHTML = '';

    if (history.length === 0) {
      tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: var(--text-muted); padding: 20px;">Журнал пуст</td></tr>';
      return;
    }

    history.forEach(item => {
      const tr = document.createElement('tr');
      const isReturn = item.action.includes('Возврат');
      const actionColor = isReturn ? 'var(--success-text)' : 'var(--primary)';

      tr.innerHTML = `
        <td style="color: var(--text-muted); font-size: 12px;">${escapeHtml(item.timestamp)}</td>
        <td style="color: ${actionColor}; font-weight: 600;">${escapeHtml(item.action)}</td>
        <td style="font-weight: 500;">№${escapeHtml(item.key_id)} (${escapeHtml(item.key_name)})</td>
        <td>${escapeHtml(item.user_name)}</td>
        <td style="color: var(--text-secondary); font-size: 12px;">${escapeHtml(item.details || '')}</td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: var(--danger); padding: 20px;">Ошибка загрузки истории</td></tr>';
  }
}


// ==========================================
//           УТИЛИТЫ
// ==========================================

function fetchWithAuth(url, options = {}) {
  const token = localStorage.getItem('token');
  const headers = options.headers || {};
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  options.headers = headers;
  return fetch(url, options);
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
