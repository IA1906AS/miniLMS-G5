/**
 * MiniLMS - Core Web Client Logic (State, API, Auth, Navigation, Modals & Init)
 * Hỗ trợ 3 vai trò: Sinh viên (SV), Giảng viên (GV), Quản trị viên (QT)
 */

// ================= GLOBAL STATE =================
const state = {
  token: localStorage.getItem('lms_token') || null,
  currentUser: JSON.parse(localStorage.getItem('lms_user') || 'null'),
  currentView: 'courses',
  currentCourse: null,
  currentCourseSubTab: 'forum',
  activeQuiz: null,
  quizTimerId: null,
  quizSecondsRemaining: 0,
  activeAssignment: null,
  activeTopic: null,
  searchDebounceTimer: null,
  adminDebounceTimer: null,
};

// ================= API HELPER =================
async function api(endpoint, options = {}) {
  const headers = options.headers || {};
  if (state.token) {
    headers['Authorization'] = `Bearer ${state.token}`;
  }

  if (!(options.body instanceof FormData) && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json';
  }

  const response = await fetch(endpoint, {
    ...options,
    headers,
  });

  if (response.status === 401) {
    localStorage.removeItem('lms_token');
    localStorage.removeItem('lms_user');
    window.location.href = '/login';
    throw new Error('Unauthorized');
  }

  if (response.status === 403) {
    const err = await response.json().catch(() => ({ detail: 'Không có quyền thực hiện hành động này.' }));
    showToast(err.detail || 'Từ chối truy cập do vi phạm phân quyền.', 'error');
    throw new Error(err.detail);
  }

  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: 'Đã xảy ra lỗi trên máy chủ.' }));
    const msg = typeof err.detail === 'string' ? err.detail : JSON.stringify(err.detail);
    showToast(msg || 'Lỗi xử lý yêu cầu.', 'error');
    throw new Error(msg);
  }

  const contentType = response.headers.get('content-type') || '';
  if (contentType.includes('application/json')) {
    return await response.json();
  }
  return response;
}

// ================= TOAST NOTIFICATIONS (DEDUPLICATED) =================
let lastToastMsg = '';
let lastToastTime = 0;

function showToast(message, type = 'info') {
  const now = Date.now();
  if (message === lastToastMsg && now - lastToastTime < 3000) {
    return;
  }
  lastToastMsg = message;
  lastToastTime = now;

  const container = document.getElementById('toast-container');
  if (!container) return;

  const toast = document.createElement('div');
  const colors = {
    success: 'bg-emerald-600 text-white',
    error: 'bg-red-600 text-white',
    info: 'bg-indigo-600 text-white',
    warning: 'bg-amber-600 text-white',
  };
  const icons = {
    success: 'fa-circle-check',
    error: 'fa-circle-exclamation',
    info: 'fa-circle-info',
    warning: 'fa-triangle-exclamation',
  };

  toast.className = `pointer-events-auto px-4 py-3 rounded-xl shadow-lg flex items-center space-x-3 text-xs font-medium transform transition duration-300 translate-y-2 opacity-0 ${colors[type] || colors.info}`;
  toast.innerHTML = `
    <i class="fa-solid ${icons[type] || icons.info} text-sm"></i>
    <span>${escapeHtml(message)}</span>
  `;

  container.appendChild(toast);
  requestAnimationFrame(() => {
    toast.classList.remove('translate-y-2', 'opacity-0');
  });

  setTimeout(() => {
    toast.classList.add('opacity-0', 'translate-x-full');
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

// ================= SESSION & RBAC HELPERS =================
function setSession(authData) {
  state.token = authData.access_token;
  state.currentUser = {
    id: authData.user_id,
    full_name: authData.full_name,
    role: authData.role,
  };
  localStorage.setItem('lms_token', state.token);
  localStorage.setItem('lms_user', JSON.stringify(state.currentUser));
}

function logout() {
  if (state.token) {
    fetch('/api/auth/logout', {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${state.token}` },
    }).catch(() => {});
  }
  state.token = null;
  state.currentUser = null;
  localStorage.removeItem('lms_token');
  localStorage.removeItem('lms_user');
  window.location.href = '/login';
}

function getRoleLabel(role) {
  switch (role) {
    case 'SV': return 'Sinh viên (SV)';
    case 'GV': return 'Giảng viên (GV)';
    case 'QT': return 'Quản trị viên (QT)';
    default: return role || 'Khách';
  }
}

function getRoleBadgeHtml(role) {
  switch (role) {
    case 'SV':
      return `<span class="px-2.5 py-0.5 rounded-full text-xs font-bold bg-sky-100 text-sky-800 border border-sky-300"><i class="fa-solid fa-user-graduate mr-1"></i> Sinh viên (SV)</span>`;
    case 'GV':
      return `<span class="px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800 border border-emerald-300"><i class="fa-solid fa-chalkboard-user mr-1"></i> Giảng viên (GV)</span>`;
    case 'QT':
      return `<span class="px-2.5 py-0.5 rounded-full text-xs font-bold bg-purple-100 text-purple-800 border border-purple-300"><i class="fa-solid fa-shield-halved mr-1"></i> Quản trị viên (QT)</span>`;
    default:
      return `<span class="px-2 py-0.5 rounded-full text-xs font-bold bg-slate-100 text-slate-700">Khách</span>`;
  }
}

function updateNavState() {
  const loggedInContainer = document.getElementById('user-logged-in');
  const loggedOutContainer = document.getElementById('user-logged-out');
  const roleBadge = document.getElementById('user-role-badge');
  const displayName = document.getElementById('user-display-name');
  const displayEmail = document.getElementById('user-display-email');
  const mobileName = document.getElementById('user-mobile-name');
  const mobileRole = document.getElementById('user-mobile-role');
  const tabAdmin = document.getElementById('tab-admin');
  const tabMyGrades = document.getElementById('tab-my-grades');
  const btnCreateCourse = document.getElementById('btn-open-create-course');
  const btnEnroll = document.getElementById('btn-open-enroll');

  if (state.token && state.currentUser) {
    loggedInContainer.classList.remove('hidden');
    loggedOutContainer.classList.add('hidden');

    roleBadge.innerHTML = getRoleBadgeHtml(state.currentUser.role);
    displayName.textContent = state.currentUser.full_name;
    displayEmail.textContent = state.currentUser.email || '';
    if (mobileName) mobileName.textContent = state.currentUser.full_name;
    if (mobileRole) mobileRole.textContent = getRoleLabel(state.currentUser.role);

    if (state.currentUser.role === 'QT') {
      tabAdmin.classList.remove('hidden');
      btnCreateCourse.classList.remove('hidden');
      btnCreateCourse.classList.add('flex');
      btnEnroll.classList.add('hidden');
      tabMyGrades.classList.add('hidden');
    } else if (state.currentUser.role === 'GV') {
      tabAdmin.classList.add('hidden');
      btnCreateCourse.classList.remove('hidden');
      btnCreateCourse.classList.add('flex');
      btnEnroll.classList.add('hidden');
      tabMyGrades.classList.add('hidden');
    } else {
      tabAdmin.classList.add('hidden');
      btnCreateCourse.classList.add('hidden');
      btnEnroll.classList.remove('hidden');
      btnEnroll.classList.add('flex');
      tabMyGrades.classList.remove('hidden');
    }
  } else {
    loggedInContainer.classList.add('hidden');
    loggedOutContainer.classList.remove('hidden');
    tabAdmin.classList.add('hidden');
    tabMyGrades.classList.add('hidden');
    btnCreateCourse.classList.add('hidden');
    btnEnroll.classList.add('hidden');
  }
}

// ================= NAVIGATION =================
function navigateTo(viewName) {
  state.currentView = viewName;
  document.getElementById('view-courses').classList.add('hidden');
  document.getElementById('view-course-detail').classList.add('hidden');
  document.getElementById('view-my-grades').classList.add('hidden');
  document.getElementById('view-admin').classList.add('hidden');

  document.querySelectorAll('.nav-tab').forEach(t => {
    t.classList.remove('text-indigo-600', 'bg-indigo-50', 'font-bold');
  });

  if (viewName === 'courses') {
    document.getElementById('view-courses').classList.remove('hidden');
    document.getElementById('tab-courses')?.classList.add('text-indigo-600', 'bg-indigo-50', 'font-bold');
    loadCourses();
  } else if (viewName === 'course-detail') {
    document.getElementById('view-course-detail').classList.remove('hidden');
  } else if (viewName === 'my-grades') {
    if (!state.currentUser || state.currentUser.role !== 'SV') {
      showToast('Sổ điểm cá nhân chỉ áp dụng cho Sinh viên (SV)', 'warning');
      navigateTo('courses');
      return;
    }
    document.getElementById('view-my-grades').classList.remove('hidden');
    document.getElementById('tab-my-grades')?.classList.add('text-indigo-600', 'bg-indigo-50', 'font-bold');
    loadMyGrades();
  } else if (viewName === 'admin') {
    if (!state.currentUser || state.currentUser.role !== 'QT') {
      showToast('Khu vực này yêu cầu quyền Quản trị viên (QT).', 'error');
      navigateTo('courses');
      return;
    }
    document.getElementById('view-admin').classList.remove('hidden');
    document.getElementById('tab-admin')?.classList.add('text-purple-700', 'bg-purple-50', 'font-bold');
    loadAdminUsers();
  }
}

// ================= MODAL CONTROLS =================
function openModal(id) { document.getElementById(id)?.classList.remove('hidden'); }
function closeModal(id) { document.getElementById(id)?.classList.add('hidden'); }
function closeAllModals() { document.querySelectorAll('[id^="modal-"]').forEach(m => m.classList.add('hidden')); }
function openEnrollModal() { openModal('modal-enroll'); }
function openCreateCourseModal() { openModal('modal-create-course'); }
function openUploadMaterialModal() { openModal('modal-upload-material'); }
function openCreateAssignmentModal() { openModal('modal-create-assignment'); }
function openCreateAnnouncementModal() { openModal('modal-create-announcement'); }
function openCreateTopicModal() { openModal('modal-create-topic'); }
function openChangePasswordModal() { openModal('modal-change-password'); }

function openCreateQuizModal() {
  const container = document.getElementById('quiz-questions-builder');
  if (container) container.innerHTML = '';
  questionCounter = 0;
  addQuizQuestionBuilder();
  openModal('modal-create-quiz');
}

async function openProfileModal() {
  try {
    const user = await api('/api/users/me');
    document.getElementById('prof-fullname').value = user.full_name;
    document.getElementById('prof-email').value = user.email;
    document.getElementById('prof-role').value = getRoleLabel(user.role);
    document.getElementById('prof-bio').value = user.bio || '';
    document.getElementById('prof-contact').value = user.contact_info || '';
    openModal('modal-profile');
  } catch (e) {
    showToast('Lỗi tải thông tin cá nhân: ' + e.message, 'error');
  }
}

function toggleUserDropdown(forceState) {
  const menu = document.getElementById('user-dropdown');
  if (typeof forceState === 'boolean') menu.classList.toggle('hidden', !forceState);
  else menu.classList.toggle('hidden');
}

// ================= UTILITIES & INIT =================
function escapeHtml(str) {
  if (!str) return '';
  return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#039;');
}

function formatDate(isoStr) {
  if (!isoStr) return '';
  try {
    return new Date(isoStr).toLocaleString('vi-VN', { hour: '2-digit', minute: '2-digit', day: '2-digit', month: '2-digit', year: 'numeric' });
  } catch {
    return isoStr;
  }
}

document.addEventListener('click', (e) => {
  const dropdown = document.getElementById('user-dropdown');
  const userButton = e.target.closest('#user-logged-in button');
  if (!userButton && dropdown && !dropdown.contains(e.target)) dropdown.classList.add('hidden');
});

async function initApp() {
  if (!state.token) {
    window.location.href = '/login';
    return;
  }
  updateNavState();
  try {
    const me = await api('/api/users/me');
    state.currentUser = me;
    localStorage.setItem('lms_user', JSON.stringify(me));
    updateNavState();
    loadCourses();
  } catch {
    localStorage.removeItem('lms_token');
    localStorage.removeItem('lms_user');
    window.location.href = '/login';
  }
}

window.addEventListener('DOMContentLoaded', () => initApp());
