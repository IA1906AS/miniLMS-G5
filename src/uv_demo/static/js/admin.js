/**
 * MiniLMS - Admin Portal Module (QT Only)
 */

function switchAdminSubTab(subTab) {
  const tabs = ['users', 'courses', 'audit'];
  tabs.forEach(t => {
    document.getElementById(`admin-pane-${t}`)?.classList.add('hidden');
    const b = document.getElementById(`admin-tab-${t}`);
    if (b) {
      b.classList.remove('text-purple-700', 'bg-purple-50');
      b.classList.add('text-slate-600');
    }
  });

  document.getElementById(`admin-pane-${subTab}`)?.classList.remove('hidden');
  const activeBtn = document.getElementById(`admin-tab-${subTab}`);
  if (activeBtn) {
    activeBtn.classList.add('text-purple-700', 'bg-purple-50');
    activeBtn.classList.remove('text-slate-600');
  }

  if (subTab === 'users') loadAdminUsers();
  else if (subTab === 'courses') loadAdminCourses();
  else if (subTab === 'audit') loadAdminAuditLogs();
}

async function loadAdminUsers() {
  const tbody = document.getElementById('admin-users-table');
  tbody.innerHTML = `<tr><td colspan="6" class="py-4 text-center text-slate-400">Đang tải người dùng...</td></tr>`;

  const search = document.getElementById('admin-user-search')?.value || '';
  const role = document.getElementById('admin-role-filter')?.value || '';

  try {
    let url = `/api/admin/users?limit=100`;
    if (search.trim()) url += `&search=${encodeURIComponent(search.trim())}`;
    if (role.trim()) url += `&role=${encodeURIComponent(role.trim())}`;

    const users = await api(url);
    tbody.innerHTML = users.map(u => `
      <tr class="hover:bg-slate-50">
        <td class="py-3 px-4 font-mono font-bold text-slate-600">#${u.id}</td>
        <td class="py-3 px-4 font-semibold text-slate-800">${escapeHtml(u.full_name)}</td>
        <td class="py-3 px-4 text-slate-500">${escapeHtml(u.email)}</td>
        <td class="py-3 px-4">
          <select onchange="adminUpdateUserRole(${u.id}, this.value)" class="text-xs px-2 py-1 border rounded bg-slate-50 font-semibold focus:outline-none">
            <option value="SV" ${u.role === 'SV' ? 'selected' : ''}>Sinh viên (SV)</option>
            <option value="GV" ${u.role === 'GV' ? 'selected' : ''}>Giảng viên (GV)</option>
            <option value="QT" ${u.role === 'QT' ? 'selected' : ''}>Quản trị viên (QT)</option>
          </select>
        </td>
        <td class="py-3 px-4">
          ${u.is_active ?
            '<span class="px-2 py-0.5 rounded text-[11px] font-bold bg-emerald-100 text-emerald-800">Hoạt động</span>' :
            '<span class="px-2 py-0.5 rounded text-[11px] font-bold bg-red-100 text-red-800">Bị khóa</span>'}
        </td>
        <td class="py-3 px-4 text-right">
          <button onclick="adminToggleUserLock(${u.id}, ${!u.is_active})" class="px-2.5 py-1 rounded text-xs font-semibold transition ${u.is_active ? 'bg-amber-50 text-amber-700 hover:bg-amber-100' : 'bg-emerald-50 text-emerald-700 hover:bg-emerald-100'}">
            ${u.is_active ? '<i class="fa-solid fa-lock mr-1"></i> Khóa' : '<i class="fa-solid fa-lock-open mr-1"></i> Mở khóa'}
          </button>
        </td>
      </tr>
    `).join('');
  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="6" class="py-4 text-center text-red-500 text-xs">Lỗi: ${escapeHtml(e.message)}</td></tr>`;
  }
}

function debounceAdminUsers() {
  clearTimeout(state.adminDebounceTimer);
  state.adminDebounceTimer = setTimeout(() => loadAdminUsers(), 300);
}

async function adminUpdateUserRole(userId, newRole) {
  try {
    await api(`/api/admin/users/${userId}/role`, {
      method: 'PUT',
      body: JSON.stringify({ role: newRole }),
    });
    showToast(`Đã thay đổi vai trò người dùng thành ${getRoleLabel(newRole)}`, 'success');
  } catch (e) {
    showToast('Lỗi thay đổi vai trò: ' + e.message, 'error');
    loadAdminUsers();
  }
}

async function adminToggleUserLock(userId, newStatus) {
  try {
    await api(`/api/admin/users/${userId}/lock`, {
      method: 'PUT',
      body: JSON.stringify({ is_active: newStatus }),
    });
    showToast(newStatus ? 'Đã mở khóa tài khoản thành công.' : 'Đã khóa tài khoản người dùng.', 'info');
    loadAdminUsers();
  } catch (e) {
    showToast('Lỗi: ' + e.message, 'error');
  }
}

async function loadAdminCourses() {
  const tbody = document.getElementById('admin-courses-table');
  tbody.innerHTML = `<tr><td colspan="5" class="py-4 text-center text-slate-400">Đang tải danh sách khóa học...</td></tr>`;

  try {
    const courses = await api('/api/admin/courses');
    tbody.innerHTML = courses.map(c => `
      <tr class="hover:bg-slate-50">
        <td class="py-3 px-4 font-mono font-bold text-indigo-700">${escapeHtml(c.code)}</td>
        <td class="py-3 px-4 font-semibold text-slate-800">${escapeHtml(c.title)}</td>
        <td class="py-3 px-4 text-slate-600">${escapeHtml(c.instructor_name || 'GV')}</td>
        <td class="py-3 px-4 text-slate-400">${formatDate(c.created_at)}</td>
        <td class="py-3 px-4 text-right">
          <button onclick="adminDeleteCourse(${c.id}, '${escapeHtml(c.code)}')" class="px-2.5 py-1 rounded text-xs font-semibold bg-red-50 text-red-600 hover:bg-red-100 transition">
            <i class="fa-solid fa-trash-can mr-1"></i> Xóa
          </button>
        </td>
      </tr>
    `).join('');
  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="5" class="py-4 text-center text-red-500 text-xs">Lỗi: ${escapeHtml(e.message)}</td></tr>`;
  }
}

async function adminDeleteCourse(courseId, code) {
  if (!confirm(`Bạn có chắc chắn muốn gỡ bỏ khóa học ${code} trên toàn hệ thống không?`)) return;
  try {
    const res = await api(`/api/admin/courses/${courseId}`, { method: 'DELETE' });
    showToast(res.message, 'success');
    loadAdminCourses();
  } catch (e) {
    showToast('Lỗi gỡ khóa học: ' + e.message, 'error');
  }
}

async function loadAdminAuditLogs() {
  const tbody = document.getElementById('admin-audit-table');
  tbody.innerHTML = `<tr><td colspan="6" class="py-4 text-center text-slate-400">Đang tải nhật ký kiểm toán...</td></tr>`;

  try {
    const logs = await api('/api/admin/audit-logs?limit=50');
    tbody.innerHTML = logs.map(l => `
      <tr class="hover:bg-slate-50">
        <td class="py-2 px-4 text-slate-400">${formatDate(l.timestamp)}</td>
        <td class="py-2 px-4 font-bold text-indigo-700">${escapeHtml(l.action)}</td>
        <td class="py-2 px-4 text-slate-700">${escapeHtml(l.entity_type)} #${l.entity_id || '-'}</td>
        <td class="py-2 px-4 text-slate-500">User #${l.user_id || '-'}</td>
        <td class="py-2 px-4 text-slate-800">${escapeHtml(l.details || '-')}</td>
        <td class="py-2 px-4 text-slate-400 font-mono">${escapeHtml(l.ip_address || '-')}</td>
      </tr>
    `).join('');
  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="6" class="py-4 text-center text-red-500 text-xs">Lỗi: ${escapeHtml(e.message)}</td></tr>`;
  }
}
