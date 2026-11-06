/**
 * MiniLMS - Web Client Application Logic
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

  // Nếu không phải FormData thì mặc định Content-Type là application/json
  if (!(options.body instanceof FormData) && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json';
  }

  const response = await fetch(endpoint, {
    ...options,
    headers,
  });

  if (response.status === 401) {
    // Hết phiên hoặc token không hợp lệ
    logout(false);
    showToast('Phiên làm việc đã hết hạn. Vui lòng đăng nhập lại.', 'error');
    openLoginModal();
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

  // Nếu là file download thì trả về blob hoặc response
  const contentType = response.headers.get('content-type') || '';
  if (contentType.includes('application/json')) {
    return await response.json();
  }
  return response;
}

// ================= TOAST NOTIFICATIONS =================
function showToast(message, type = 'info') {
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

// ================= AUTHENTICATION & QUICK DEMO =================
async function quickLogin(email, password) {
  try {
    const res = await api('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    setSession(res);
    showToast(`Đăng nhập thành công với vai trò ${getRoleLabel(res.role)}!`, 'success');
    closeAllModals();
    await initApp();
  } catch (e) {
    console.error('Quick login error:', e);
  }
}

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

function logout(notify = true) {
  if (state.token) {
    // Thu hồi token trên máy chủ (chống lạm dụng token)
    api('/api/auth/logout', { method: 'POST' }).catch(() => {});
  }
  state.token = null;
  state.currentUser = null;
  localStorage.removeItem('lms_token');
  localStorage.removeItem('lms_user');
  if (notify) showToast('Đã đăng xuất khỏi hệ thống.', 'info');
  updateNavState();
  navigateTo('courses');
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

    // Quyền Quản trị viên (QT)
    if (state.currentUser.role === 'QT') {
      tabAdmin.classList.remove('hidden');
      btnCreateCourse.classList.remove('hidden');
      btnCreateCourse.classList.add('flex');
      btnEnroll.classList.add('hidden');
      tabMyGrades.classList.add('hidden');
    }
    // Quyền Giảng viên (GV)
    else if (state.currentUser.role === 'GV') {
      tabAdmin.classList.add('hidden');
      btnCreateCourse.classList.remove('hidden');
      btnCreateCourse.classList.add('flex');
      btnEnroll.classList.add('hidden');
      tabMyGrades.classList.add('hidden');
    }
    // Quyền Sinh viên (SV)
    else {
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

  // Update tabs style
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

// ================= VIEW 1: COURSES CATALOG =================
async function loadCourses(search = '') {
  const grid = document.getElementById('courses-grid');
  grid.innerHTML = `<div class="col-span-full py-12 text-center text-slate-400"><i class="fa-solid fa-spinner fa-spin mr-2"></i> Đang tải danh sách khóa học...</div>`;

  try {
    let url = '/api/courses';
    if (search.trim()) {
      url += `?search=${encodeURIComponent(search.trim())}`;
    }
    const courses = await api(url);

    if (courses.length === 0) {
      grid.innerHTML = `
        <div class="col-span-full py-12 text-center bg-white rounded-2xl border border-slate-200 p-8">
          <div class="w-12 h-12 mx-auto rounded-full bg-slate-100 flex items-center justify-center text-slate-400 mb-3">
            <i class="fa-solid fa-folder-open text-xl"></i>
          </div>
          <p class="text-sm font-semibold text-slate-700">Không tìm thấy khóa học nào</p>
          <p class="text-xs text-slate-400 mt-1">Hãy thử tìm với từ khóa khác hoặc tạo khóa học mới nếu bạn là Giảng viên / Quản trị viên.</p>
        </div>
      `;
      return;
    }

    grid.innerHTML = courses.map(c => `
      <div class="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm hover:shadow-md transition flex flex-col justify-between group">
        <div class="space-y-3">
          <div class="flex items-center justify-between">
            <span class="px-2.5 py-1 rounded-lg text-xs font-mono font-bold bg-indigo-50 text-indigo-700 border border-indigo-100">${escapeHtml(c.code)}</span>
            <span class="text-[11px] text-emerald-600 font-medium flex items-center"><i class="fa-solid fa-circle text-[6px] mr-1"></i> Đang mở</span>
          </div>
          <div>
            <h3 class="text-base font-bold text-slate-900 group-hover:text-indigo-600 transition leading-snug cursor-pointer" onclick="openCourseDetail(${c.id})">${escapeHtml(c.title)}</h3>
            <p class="text-xs text-slate-500 line-clamp-2 mt-1.5 leading-relaxed">${escapeHtml(c.description || 'Chưa có mô tả cho khóa học này.')}</p>
          </div>
        </div>

        <div class="pt-4 mt-4 border-t border-slate-100 flex items-center justify-between">
          <div class="flex items-center space-x-2 text-xs text-slate-600">
            <div class="w-6 h-6 rounded-full bg-slate-100 flex items-center justify-center text-slate-500 font-bold text-[10px]">
              <i class="fa-solid fa-chalkboard-user"></i>
            </div>
            <span class="font-medium truncate max-w-[140px]">${escapeHtml(c.instructor_name || 'GV')}</span>
          </div>

          <button onclick="openCourseDetail(${c.id})" class="px-3 py-1.5 rounded-xl bg-slate-900 hover:bg-indigo-600 text-white text-xs font-semibold transition flex items-center shadow-sm">
            Vào học <i class="fa-solid fa-arrow-right ml-1.5 text-[10px]"></i>
          </button>
        </div>
      </div>
    `).join('');
  } catch (e) {
    grid.innerHTML = `<div class="col-span-full py-8 text-center text-red-500 text-xs">Không thể tải khóa học: ${escapeHtml(e.message)}</div>`;
  }
}

function debounceSearchCourses() {
  clearTimeout(state.searchDebounceTimer);
  state.searchDebounceTimer = setTimeout(() => {
    const val = document.getElementById('course-search-input').value;
    loadCourses(val);
  }, 350);
}

// ================= VIEW 2: COURSE DETAIL =================
async function openCourseDetail(courseId) {
  try {
    const course = await api(`/api/courses/${courseId}`);
    state.currentCourse = course;

    document.getElementById('detail-course-code').textContent = course.code;
    document.getElementById('detail-course-title').textContent = course.title;
    document.getElementById('detail-course-desc').textContent = course.description || 'Chưa có mô tả chi tiết.';
    document.getElementById('detail-course-instructor').textContent = course.instructor_name || 'Giảng viên';

    // Update teacher/admin controls
    const isInstructorOrAdmin = state.currentUser && (state.currentUser.role === 'QT' || (state.currentUser.role === 'GV' && course.instructor_id === state.currentUser.id));

    const btnAnnounce = document.getElementById('btn-open-create-announcement');
    const btnMaterial = document.getElementById('btn-open-upload-material');
    const btnAssign = document.getElementById('btn-open-create-assignment');
    const btnQuiz = document.getElementById('btn-open-create-quiz');
    const addStudentBox = document.getElementById('instructor-add-student-box');

    if (isInstructorOrAdmin) {
      btnAnnounce.classList.remove('hidden');
      btnMaterial.classList.remove('hidden');
      btnAssign.classList.remove('hidden');
      btnQuiz.classList.remove('hidden');
      addStudentBox.classList.remove('hidden');
    } else {
      btnAnnounce.classList.add('hidden');
      btnMaterial.classList.add('hidden');
      btnAssign.classList.add('hidden');
      btnQuiz.classList.add('hidden');
      addStudentBox.classList.add('hidden');
    }

    navigateTo('course-detail');
    switchCourseSubTab('forum');
  } catch (e) {
    console.error('Cannot open course detail:', e);
  }
}

function switchCourseSubTab(tabName) {
  state.currentCourseSubTab = tabName;
  const tabs = ['forum', 'materials', 'assignments', 'quizzes', 'members', 'gradebook'];

  tabs.forEach(t => {
    const pane = document.getElementById(`pane-${t}`);
    const btn = document.getElementById(`subtab-${t}`);
    if (pane) pane.classList.add('hidden');
    if (btn) {
      btn.classList.remove('text-indigo-600', 'bg-indigo-50');
      btn.classList.add('text-slate-600');
    }
  });

  const activePane = document.getElementById(`pane-${tabName}`);
  const activeBtn = document.getElementById(`subtab-${tabName}`);
  if (activePane) activePane.classList.remove('hidden');
  if (activeBtn) {
    activeBtn.classList.add('text-indigo-600', 'bg-indigo-50');
    activeBtn.classList.remove('text-slate-600');
  }

  if (tabName === 'forum') loadCourseForumAndAnnouncements();
  else if (tabName === 'materials') loadCourseMaterials();
  else if (tabName === 'assignments') loadCourseAssignments();
  else if (tabName === 'quizzes') loadCourseQuizzes();
  else if (tabName === 'members') loadCourseMembers();
  else if (tabName === 'gradebook') loadCourseGradebook();
}

// ---------------- SUB-TAB 1: FORUM & ANNOUNCEMENTS ----------------
async function loadCourseForumAndAnnouncements() {
  if (!state.currentCourse) return;
  const courseId = state.currentCourse.id;

  // 1. Announcements
  const annList = document.getElementById('announcements-list');
  try {
    const ann = await api(`/api/courses/${courseId}/announcements`);
    if (ann.length === 0) {
      annList.innerHTML = `<p class="text-xs text-amber-800/80 italic">Chưa có thông báo nào được đăng.</p>`;
    } else {
      annList.innerHTML = ann.map(a => `
        <div class="bg-white/80 p-3 rounded-xl border border-amber-200/80 space-y-1">
          <div class="flex items-center justify-between text-xs">
            <span class="font-bold text-slate-800">${escapeHtml(a.title)}</span>
            <span class="text-[11px] text-slate-400">${formatDate(a.created_at)}</span>
          </div>
          <p class="text-xs text-slate-600 leading-relaxed">${escapeHtml(a.content)}</p>
        </div>
      `).join('');
    }
  } catch (e) {
    annList.innerHTML = `<p class="text-xs text-red-500">Lỗi tải thông báo: ${escapeHtml(e.message)}</p>`;
  }

  // 2. Topics
  const topicList = document.getElementById('topics-list');
  try {
    const topics = await api(`/api/courses/${courseId}/topics`);
    if (topics.length === 0) {
      topicList.innerHTML = `
        <div class="py-8 text-center text-slate-400 text-xs">
          Chưa có chủ đề thảo luận nào. Hãy là người đầu tiên đặt câu hỏi!
        </div>
      `;
    } else {
      topicList.innerHTML = topics.map(t => `
        <div class="pt-3 pb-2 flex items-start justify-between gap-4 cursor-pointer hover:bg-slate-50/80 p-2 rounded-xl transition" onclick="openTopicDetail(${t.id})">
          <div class="space-y-1">
            <h4 class="text-sm font-semibold text-slate-800 hover:text-indigo-600 transition">${escapeHtml(t.title)}</h4>
            <div class="flex items-center space-x-3 text-xs text-slate-400">
              <span>Đăng bởi: <b class="text-slate-600">${escapeHtml(t.author_name || 'Thành viên')}</b></span>
              <span>•</span>
              <span>${formatDate(t.created_at)}</span>
            </div>
          </div>
          <div class="flex items-center space-x-1.5 px-2.5 py-1 rounded-lg bg-indigo-50 text-indigo-700 text-xs font-semibold">
            <i class="fa-regular fa-comment-dots"></i>
            <span>${(t.comments || []).length}</span>
          </div>
        </div>
      `).join('');
    }
  } catch (e) {
    topicList.innerHTML = `<p class="text-xs text-red-500">Lỗi tải diễn đàn: ${escapeHtml(e.message)}</p>`;
  }
}

async function openTopicDetail(topicId) {
  if (!state.currentCourse) return;
  try {
    const topics = await api(`/api/courses/${state.currentCourse.id}/topics`);
    const topic = topics.find(t => t.id === topicId);
    if (!topic) return;

    state.activeTopic = topic;
    document.getElementById('modal-topic-title').textContent = topic.title;
    document.getElementById('modal-topic-author').textContent = topic.author_name || 'Thành viên';
    document.getElementById('modal-topic-time').textContent = formatDate(topic.created_at);
    document.getElementById('modal-topic-content').textContent = topic.content;
    document.getElementById('modal-topic-comment-count').textContent = (topic.comments || []).length;

    renderTopicComments(topic.comments || []);
    openModal('modal-topic-detail');
  } catch (e) {
    showToast('Không thể mở chủ đề: ' + e.message, 'error');
  }
}

function renderTopicComments(comments) {
  const container = document.getElementById('modal-topic-comments');
  if (comments.length === 0) {
    container.innerHTML = `<p class="text-xs text-slate-400 italic py-2">Chưa có bình luận nào.</p>`;
    return;
  }
  container.innerHTML = comments.map(c => `
    <div class="bg-slate-50 p-3 rounded-xl border border-slate-200/60 space-y-1 text-xs">
      <div class="flex items-center justify-between text-slate-500">
        <span class="font-bold text-slate-800">${escapeHtml(c.author_name || 'Thành viên')}</span>
        <span class="text-[10px]">${formatDate(c.created_at)}</span>
      </div>
      <p class="text-slate-700 leading-relaxed">${escapeHtml(c.content)}</p>
    </div>
  `).join('');
}

// ---------------- SUB-TAB 2: MATERIALS ----------------
async function loadCourseMaterials() {
  if (!state.currentCourse) return;
  const list = document.getElementById('materials-list');
  list.innerHTML = `<div class="py-6 text-center text-slate-400 text-xs"><i class="fa-solid fa-spinner fa-spin mr-1"></i> Đang tải tài liệu...</div>`;

  try {
    const materials = await api(`/api/courses/${state.currentCourse.id}/materials`);
    if (materials.length === 0) {
      list.innerHTML = `<div class="py-8 text-center text-slate-400 text-xs">Chưa có tài liệu nào được tải lên cho khóa học này.</div>`;
      return;
    }

    list.innerHTML = materials.map(m => `
      <div class="py-3 flex items-center justify-between gap-4">
        <div class="flex items-center space-x-3">
          <div class="w-10 h-10 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center font-bold">
            <i class="fa-solid fa-file-pdf"></i>
          </div>
          <div>
            <h4 class="text-sm font-bold text-slate-800">${escapeHtml(m.title)}</h4>
            <div class="text-[11px] text-slate-400">Tệp: ${escapeHtml(m.filename)} • Đăng ngày ${formatDate(m.created_at)}</div>
          </div>
        </div>

        <button onclick="downloadMaterial(${m.id}, '${escapeHtml(m.filename)}')" class="px-3 py-1.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold transition flex items-center">
          <i class="fa-solid fa-download mr-1.5"></i> Tải về
        </button>
      </div>
    `).join('');
  } catch (e) {
    list.innerHTML = `<p class="text-xs text-red-500 py-4">Lỗi: ${escapeHtml(e.message)}</p>`;
  }
}

async function downloadMaterial(materialId, filename) {
  try {
    const response = await fetch(`/api/courses/materials/${materialId}/download`, {
      headers: { Authorization: `Bearer ${state.token}` }
    });
    if (!response.ok) throw new Error('Không thể tải tệp');
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
    showToast(`Đang tải xuống: ${filename}`, 'success');
  } catch (e) {
    showToast('Lỗi tải tệp tài liệu: ' + e.message, 'error');
  }
}

// ---------------- SUB-TAB 3: ASSIGNMENTS ----------------
async function loadCourseAssignments() {
  if (!state.currentCourse) return;
  const list = document.getElementById('assignments-list');
  list.innerHTML = `<div class="col-span-full py-6 text-center text-slate-400 text-xs"><i class="fa-solid fa-spinner fa-spin mr-1"></i> Đang tải bài tập...</div>`;

  try {
    const assigns = await api(`/api/courses/${state.currentCourse.id}/assignments`);
    if (assigns.length === 0) {
      list.innerHTML = `<div class="col-span-full py-8 text-center text-slate-400 text-xs">Chưa có bài tập nào được giao.</div>`;
      return;
    }

    list.innerHTML = assigns.map(a => `
      <div class="p-4 rounded-xl border border-slate-200 bg-slate-50/50 hover:bg-white hover:border-indigo-300 transition space-y-3 cursor-pointer" onclick="openAssignmentDetail(${a.id})">
        <div class="flex items-center justify-between">
          <span class="px-2 py-0.5 rounded text-[11px] font-semibold bg-indigo-100 text-indigo-700">Điểm tối đa: ${a.max_score}</span>
          <span class="text-xs text-slate-500"><i class="fa-regular fa-clock mr-1"></i> ${formatDate(a.deadline)}</span>
        </div>
        <div>
          <h4 class="text-sm font-bold text-slate-900">${escapeHtml(a.title)}</h4>
          <p class="text-xs text-slate-500 line-clamp-2 mt-1">${escapeHtml(a.description || '')}</p>
        </div>
        <div class="flex justify-end">
          <span class="text-xs font-semibold text-indigo-600 flex items-center">Xem chi tiết & nộp bài <i class="fa-solid fa-chevron-right ml-1 text-[10px]"></i></span>
        </div>
      </div>
    `).join('');
  } catch (e) {
    list.innerHTML = `<p class="col-span-full text-xs text-red-500 py-4">Lỗi: ${escapeHtml(e.message)}</p>`;
  }
}

async function openAssignmentDetail(assignId) {
  try {
    const a = await api(`/api/assignments/${assignId}`);
    state.activeAssignment = a;

    document.getElementById('modal-assign-title').textContent = a.title;
    document.getElementById('modal-assign-desc').textContent = a.description || 'Không có mô tả thêm.';
    document.getElementById('modal-assign-deadline').textContent = formatDate(a.deadline);
    document.getElementById('modal-assign-max-score').textContent = a.max_score + ' điểm';

    const isStudent = state.currentUser && state.currentUser.role === 'SV';
    const isTeacherOrAdmin = state.currentUser && (state.currentUser.role === 'GV' || state.currentUser.role === 'QT');

    const studentView = document.getElementById('assign-student-view');
    const teacherView = document.getElementById('assign-teacher-view');

    if (isStudent) {
      studentView.classList.remove('hidden');
      teacherView.classList.add('hidden');
      await loadStudentSubmission(a.id);
    } else if (isTeacherOrAdmin) {
      studentView.classList.add('hidden');
      teacherView.classList.remove('hidden');
      await loadTeacherSubmissionsList(a.id);
    }

    openModal('modal-assignment-detail');
  } catch (e) {
    showToast('Không thể mở chi tiết bài tập: ' + e.message, 'error');
  }
}

async function loadStudentSubmission(assignId) {
  const container = document.getElementById('student-submission-status');
  container.innerHTML = `<p class="text-xs text-slate-400"><i class="fa-solid fa-spinner fa-spin mr-1"></i> Đang kiểm tra bài nộp...</p>`;

  try {
    const sub = await api(`/api/assignments/${assignId}/my-submission`);
    if (!sub || !sub.id) {
      container.className = 'p-4 rounded-xl border border-amber-200 bg-amber-50 text-xs text-amber-800 space-y-1';
      container.innerHTML = `
        <div class="font-bold flex items-center"><i class="fa-solid fa-clock mr-1.5"></i> Bạn chưa nộp bài tập này</div>
        <p class="text-amber-700">Vui lòng chọn tệp và ấn nút "Nộp bài tập" bên dưới trước hạn chót.</p>
      `;
    } else {
      const graded = sub.score !== null;
      container.className = `p-4 rounded-xl border text-xs space-y-2 ${graded ? 'border-emerald-200 bg-emerald-50' : 'border-sky-200 bg-sky-50'}`;
      container.innerHTML = `
        <div class="flex items-center justify-between">
          <span class="font-bold text-slate-800"><i class="fa-solid fa-file-arrow-up mr-1 text-sky-600"></i> Đã nộp tệp: ${escapeHtml(sub.filename)}</span>
          <span class="text-slate-500">${formatDate(sub.submitted_at)}</span>
        </div>
        ${graded ? `
          <div class="pt-2 border-t border-emerald-200 text-emerald-900">
            <div class="font-bold text-sm"><i class="fa-solid fa-award mr-1"></i> Điểm số: ${sub.score} / ${state.activeAssignment.max_score}</div>
            <p class="text-emerald-700 mt-0.5">Nhận xét: "${escapeHtml(sub.feedback || 'Bài làm đạt yêu cầu.')}"</p>
          </div>
        ` : `
          <div class="text-sky-700 italic">Đang chờ Giảng viên chấm điểm và phản hồi.</div>
        `}
      `;
    }
  } catch (e) {
    container.innerHTML = `<p class="text-xs text-red-500">Lỗi kiểm tra bài nộp: ${escapeHtml(e.message)}</p>`;
  }
}

async function loadTeacherSubmissionsList(assignId) {
  const table = document.getElementById('assign-submissions-table');
  table.innerHTML = `<tr><td colspan="6" class="py-4 text-center text-slate-400">Đang tải danh sách bài nộp...</td></tr>`;

  try {
    const subs = await api(`/api/assignments/${assignId}/submissions`);
    if (subs.length === 0) {
      table.innerHTML = `<tr><td colspan="6" class="py-6 text-center text-slate-400 italic">Chưa có sinh viên nào nộp bài tập này.</td></tr>`;
      return;
    }

    table.innerHTML = subs.map(s => `
      <tr class="hover:bg-slate-50">
        <td class="py-2.5 px-3 font-semibold text-slate-800">${escapeHtml(s.student_name || 'SV #' + s.student_id)}</td>
        <td class="py-2.5 px-3">
          <button onclick="downloadSubmission(${s.id}, '${escapeHtml(s.filename)}')" class="text-indigo-600 hover:underline flex items-center">
            <i class="fa-solid fa-download mr-1"></i> ${escapeHtml(s.filename)}
          </button>
        </td>
        <td class="py-2.5 px-3 text-slate-500">${formatDate(s.submitted_at)}</td>
        <td class="py-2.5 px-3">
          <input type="number" id="grade-score-${s.id}" min="0" max="${state.activeAssignment.max_score}" step="0.25" value="${s.score !== null ? s.score : ''}" placeholder="0 - ${state.activeAssignment.max_score}" class="w-20 px-2 py-1 border rounded text-xs">
        </td>
        <td class="py-2.5 px-3">
          <input type="text" id="grade-feedback-${s.id}" value="${escapeHtml(s.feedback || '')}" placeholder="Nhận xét bài làm..." class="w-48 px-2 py-1 border rounded text-xs">
        </td>
        <td class="py-2.5 px-3 text-right">
          <button onclick="submitGrade(${s.id})" class="px-2.5 py-1 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold rounded text-xs transition">
            Chấm
          </button>
        </td>
      </tr>
    `).join('');
  } catch (e) {
    table.innerHTML = `<tr><td colspan="6" class="py-4 text-center text-red-500 text-xs">Lỗi: ${escapeHtml(e.message)}</td></tr>`;
  }
}

async function downloadSubmission(subId, filename) {
  try {
    const response = await fetch(`/api/submissions/${subId}/download`, {
      headers: { Authorization: `Bearer ${state.token}` }
    });
    if (!response.ok) throw new Error('Không có quyền tải bài nộp hoặc tệp không tồn tại.');
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
    showToast(`Đang tải bài nộp: ${filename}`, 'success');
  } catch (e) {
    showToast('Lỗi: ' + e.message, 'error');
  }
}

async function submitGrade(subId) {
  const scoreInput = document.getElementById(`grade-score-${subId}`);
  const feedbackInput = document.getElementById(`grade-feedback-${subId}`);
  const score = parseFloat(scoreInput.value);
  const feedback = feedbackInput.value.trim();

  if (isNaN(score)) {
    showToast('Vui lòng nhập điểm số hợp lệ', 'warning');
    return;
  }

  try {
    await api(`/api/submissions/${subId}/grade`, {
      method: 'POST',
      body: JSON.stringify({ score, feedback }),
    });
    showToast('Đã lưu điểm và nhận xét thành công!', 'success');
    if (state.activeAssignment) loadTeacherSubmissionsList(state.activeAssignment.id);
  } catch (e) {
    showToast('Không thể lưu điểm: ' + e.message, 'error');
  }
}

// ---------------- SUB-TAB 4: QUIZZES ----------------
async function loadCourseQuizzes() {
  if (!state.currentCourse) return;
  const list = document.getElementById('quizzes-list');
  list.innerHTML = `<div class="col-span-full py-6 text-center text-slate-400 text-xs"><i class="fa-solid fa-spinner fa-spin mr-1"></i> Đang tải bài kiểm tra...</div>`;

  try {
    const quizzes = await api(`/api/courses/${state.currentCourse.id}/quizzes`);
    if (quizzes.length === 0) {
      list.innerHTML = `<div class="col-span-full py-8 text-center text-slate-400 text-xs">Chưa có bài kiểm tra trắc nghiệm nào.</div>`;
      return;
    }

    const isStudent = state.currentUser && state.currentUser.role === 'SV';

    list.innerHTML = quizzes.map(q => `
      <div class="p-4 rounded-xl border border-slate-200 bg-slate-50/50 hover:bg-white hover:border-indigo-300 transition space-y-3">
        <div class="flex items-center justify-between">
          <span class="px-2 py-0.5 rounded text-[11px] font-semibold bg-purple-100 text-purple-700"><i class="fa-solid fa-clock mr-1"></i> ${q.time_limit_minutes} phút</span>
          <span class="text-xs text-slate-500">Tối đa: ${q.max_attempts} lần nộp</span>
        </div>
        <div>
          <h4 class="text-sm font-bold text-slate-900">${escapeHtml(q.title)}</h4>
          <p class="text-xs text-slate-500 line-clamp-2 mt-1">${escapeHtml(q.description || '')}</p>
        </div>
        <div class="flex items-center justify-between pt-2 border-t border-slate-100">
          <span class="text-xs text-slate-400">${(q.questions || []).length} câu hỏi</span>
          ${isStudent ? `
            <button onclick="startTakeQuiz(${q.id})" class="px-3 py-1.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold transition flex items-center shadow-sm">
              <i class="fa-solid fa-play mr-1.5 text-[10px]"></i> Bắt đầu làm bài
            </button>
          ` : `
            <span class="text-xs font-medium text-slate-500 italic">Dành cho Sinh viên</span>
          `}
        </div>
      </div>
    `).join('');
  } catch (e) {
    list.innerHTML = `<p class="col-span-full text-xs text-red-500 py-4">Lỗi: ${escapeHtml(e.message)}</p>`;
  }
}

async function startTakeQuiz(quizId) {
  try {
    const quiz = await api(`/api/quizzes/${quizId}`);
    state.activeQuiz = quiz;

    document.getElementById('take-quiz-title').textContent = quiz.title;

    // Render questions - note that options NEVER have is_correct in student payload!
    const container = document.getElementById('take-quiz-questions');
    container.innerHTML = quiz.questions.map((q, idx) => `
      <div class="p-4 rounded-xl border border-slate-200 bg-slate-50 space-y-3">
        <div class="flex items-center justify-between text-xs">
          <span class="font-bold text-indigo-700">Câu hỏi ${idx + 1} (${q.points} điểm)</span>
        </div>
        <p class="text-sm font-semibold text-slate-800 leading-snug">${escapeHtml(q.content)}</p>
        <div class="space-y-2 pt-1">
          ${q.options.map(opt => `
            <label class="flex items-center space-x-3 p-2.5 rounded-lg border border-slate-200/80 bg-white hover:bg-indigo-50/50 cursor-pointer transition">
              <input type="radio" name="question_${q.id}" value="${opt.id}" class="text-indigo-600 focus:ring-indigo-500">
              <span class="text-xs text-slate-700 leading-relaxed">${escapeHtml(opt.content)}</span>
            </label>
          `).join('')}
        </div>
      </div>
    `).join('');

    // Setup live countdown timer
    state.quizSecondsRemaining = (quiz.time_limit_minutes || 15) * 60;
    updateTimerDisplay();
    clearInterval(state.quizTimerId);
    state.quizTimerId = setInterval(() => {
      state.quizSecondsRemaining--;
      updateTimerDisplay();
      if (state.quizSecondsRemaining <= 0) {
        clearInterval(state.quizTimerId);
        showToast('Hết thời gian làm bài! Hệ thống tự động nộp bài.', 'warning');
        submitQuizAnswers();
      }
    }, 1000);

    openModal('modal-take-quiz');
  } catch (e) {
    showToast('Không thể mở đề thi: ' + e.message, 'error');
  }
}

function updateTimerDisplay() {
  const m = Math.floor(state.quizSecondsRemaining / 60);
  const s = state.quizSecondsRemaining % 60;
  const str = `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
  const el = document.getElementById('quiz-countdown-timer');
  if (el) el.textContent = str;
}

async function submitQuizAnswers() {
  if (!state.activeQuiz) return;
  clearInterval(state.quizTimerId);

  const answers = [];
  state.activeQuiz.questions.forEach(q => {
    const selected = document.querySelector(`input[name="question_${q.id}"]:checked`);
    if (selected) {
      answers.push({
        question_id: q.id,
        selected_option_id: parseInt(selected.value),
      });
    }
  });

  try {
    const result = await api(`/api/quizzes/${state.activeQuiz.id}/submit`, {
      method: 'POST',
      body: JSON.stringify({ answers }),
    });

    closeModal('modal-take-quiz');
    showToast(`Chúc mừng! Bạn đã hoàn thành bài thi với số điểm: ${result.score}`, 'success');
    alert(`🎉 KẾT QUẢ BÀI THI TRẮC NGHIỆM:\n\n• Điểm số đạt được: ${result.score} điểm\n• Lần nộp thứ: ${result.attempt_number}\n• Thời gian nộp: ${formatDate(result.completed_at)}`);
  } catch (e) {
    showToast('Lỗi khi nộp bài trắc nghiệm: ' + e.message, 'error');
  }
}

// ---------------- SUB-TAB 5: MEMBERS ----------------
async function loadCourseMembers() {
  if (!state.currentCourse) return;
  const tbody = document.getElementById('course-members-table');
  tbody.innerHTML = `<tr><td colspan="3" class="py-4 text-center text-slate-400">Đang tải danh sách thành viên...</td></tr>`;

  try {
    const members = await api(`/api/users/members/course/${state.currentCourse.id}`);
    tbody.innerHTML = members.map(m => `
      <tr class="hover:bg-slate-50">
        <td class="py-3 px-4 font-semibold text-slate-800">${escapeHtml(m.full_name)}</td>
        <td class="py-3 px-4">${getRoleBadgeHtml(m.role)}</td>
        <td class="py-3 px-4 text-slate-500">${escapeHtml(m.bio || 'Chưa cập nhật')}</td>
      </tr>
    `).join('');
  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="3" class="py-4 text-center text-red-500 text-xs">Lỗi: ${escapeHtml(e.message)}</td></tr>`;
  }
}

async function instructorEnrollStudent() {
  if (!state.currentCourse) return;
  const input = document.getElementById('add-student-email');
  const email = input.value.trim();
  if (!email) return;

  try {
    const res = await api(`/api/courses/${state.currentCourse.id}/enroll-student`, {
      method: 'POST',
      body: JSON.stringify({ student_email: email }),
    });
    showToast(res.message, 'success');
    input.value = '';
    loadCourseMembers();
  } catch (e) {
    showToast('Lỗi: ' + e.message, 'error');
  }
}

// ---------------- SUB-TAB 6: GRADEBOOK ----------------
async function loadCourseGradebook() {
  if (!state.currentCourse) return;
  const container = document.getElementById('gradebook-content');
  container.innerHTML = `<div class="py-6 text-center text-slate-400 text-xs"><i class="fa-solid fa-spinner fa-spin mr-1"></i> Đang tải bảng điểm...</div>`;

  const isStudent = state.currentUser && state.currentUser.role === 'SV';

  if (isStudent) {
    try {
      const data = await api(`/api/courses/${state.currentCourse.id}/my-grades`);
      if ((data.assignments || []).length === 0) {
        container.innerHTML = `<p class="py-6 text-center text-slate-400 text-xs">Khóa học này chưa có bài tập nào cần tính điểm.</p>`;
        return;
      }

      container.innerHTML = `
        <table class="w-full text-left text-xs">
          <thead class="bg-slate-50 text-slate-500 uppercase font-semibold border-y border-slate-100">
            <tr>
              <th class="py-3 px-4">Bài tập</th>
              <th class="py-3 px-4">Hạn nộp</th>
              <th class="py-3 px-4">Trạng thái</th>
              <th class="py-3 px-4">Điểm</th>
              <th class="py-3 px-4">Nhận xét của Giảng viên</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            ${data.assignments.map(a => `
              <tr class="hover:bg-slate-50">
                <td class="py-3 px-4 font-bold text-slate-800">${escapeHtml(a.assignment_title)}</td>
                <td class="py-3 px-4 text-slate-500">${formatDate(a.deadline)}</td>
                <td class="py-3 px-4">
                  ${a.submission ? '<span class="text-emerald-600 font-semibold">Đã nộp bài</span>' : '<span class="text-amber-600 font-semibold">Chưa nộp</span>'}
                </td>
                <td class="py-3 px-4 font-bold text-indigo-700">
                  ${a.submission && a.submission.score !== null ? a.submission.score + ' / ' + a.max_score : '-'}
                </td>
                <td class="py-3 px-4 text-slate-600 italic">
                  ${a.submission && a.submission.feedback ? escapeHtml(a.submission.feedback) : '-'}
                </td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      `;
    } catch (e) {
      container.innerHTML = `<p class="text-xs text-red-500 py-4">Lỗi: ${escapeHtml(e.message)}</p>`;
    }
  } else {
    // Teacher & Admin Full Gradebook
    try {
      const data = await api(`/api/courses/${state.currentCourse.id}/gradebook`);
      if ((data.students || []).length === 0) {
        container.innerHTML = `<p class="py-6 text-center text-slate-400 text-xs">Chưa có sinh viên nào ghi danh khóa học.</p>`;
        return;
      }

      container.innerHTML = `
        <table class="w-full text-left text-xs">
          <thead class="bg-slate-50 text-slate-500 uppercase font-semibold border-y border-slate-100">
            <tr>
              <th class="py-3 px-4">Mã SV</th>
              <th class="py-3 px-4">Họ và tên</th>
              <th class="py-3 px-4">Email</th>
              <th class="py-3 px-4">Chi tiết điểm bài tập</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            ${data.students.map(s => `
              <tr class="hover:bg-slate-50">
                <td class="py-3 px-4 font-mono font-bold text-slate-700">#${s.student_id}</td>
                <td class="py-3 px-4 font-semibold text-slate-800">${escapeHtml(s.student_name)}</td>
                <td class="py-3 px-4 text-slate-500">${escapeHtml(s.student_email)}</td>
                <td class="py-3 px-4">
                  <div class="flex flex-wrap gap-2">
                    ${(s.grades || []).map(g => `
                      <span class="px-2 py-1 rounded bg-slate-100 border text-[11px]">
                        ${escapeHtml(g.assignment_title)}: <b class="${g.score !== null ? 'text-emerald-600' : 'text-slate-400'}">${g.score !== null ? g.score : 'Chưa nộp'}</b>
                      </span>
                    `).join('')}
                  </div>
                </td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      `;
    } catch (e) {
      container.innerHTML = `<p class="text-xs text-red-500 py-4">Lỗi: ${escapeHtml(e.message)}</p>`;
    }
  }
}

// ================= VIEW 3: MY GRADES (SV) =================
async function loadMyGrades() {
  const container = document.getElementById('my-grades-table-container');
  container.innerHTML = `<div class="py-8 text-center text-slate-400 text-xs"><i class="fa-solid fa-spinner fa-spin mr-1"></i> Đang tải sổ điểm cá nhân...</div>`;

  try {
    const res = await api('/api/my-grades');
    if ((res.courses || []).length === 0) {
      container.innerHTML = `<p class="py-8 text-center text-slate-400 text-xs">Bạn chưa ghi danh vào khóa học nào.</p>`;
      return;
    }

    container.innerHTML = res.courses.map(c => `
      <div class="mb-6 border border-slate-200 rounded-xl overflow-hidden">
        <div class="bg-slate-100/80 px-4 py-2.5 font-bold text-xs text-slate-800 flex items-center justify-between">
          <span><i class="fa-solid fa-book mr-2 text-indigo-600"></i> ${escapeHtml(c.course_code)}: ${escapeHtml(c.course_title)}</span>
          <span class="text-slate-500 font-normal">GV: ${escapeHtml(c.instructor_name || 'N/A')}</span>
        </div>
        <table class="w-full text-left text-xs">
          <thead class="bg-white text-slate-500 uppercase font-semibold border-b border-slate-100 text-[11px]">
            <tr>
              <th class="py-2.5 px-4">Bài tập</th>
              <th class="py-2.5 px-4">Hạn chót</th>
              <th class="py-2.5 px-4">Trạng thái</th>
              <th class="py-2.5 px-4">Điểm số</th>
              <th class="py-2.5 px-4">Nhận xét</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            ${(c.assignments || []).map(a => `
              <tr class="hover:bg-slate-50/50">
                <td class="py-2.5 px-4 font-semibold text-slate-800">${escapeHtml(a.assignment_title)}</td>
                <td class="py-2.5 px-4 text-slate-500">${formatDate(a.deadline)}</td>
                <td class="py-2.5 px-4">
                  ${a.submission ? '<span class="text-emerald-600 font-bold">Đã nộp bài</span>' : '<span class="text-amber-600 font-semibold">Chưa nộp</span>'}
                </td>
                <td class="py-2.5 px-4 font-bold text-indigo-700">
                  ${a.submission && a.submission.score !== null ? a.submission.score + ' / ' + a.max_score : '-'}
                </td>
                <td class="py-2.5 px-4 text-slate-600 italic">
                  ${a.submission && a.submission.feedback ? escapeHtml(a.submission.feedback) : '-'}
                </td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    `).join('');
  } catch (e) {
    container.innerHTML = `<p class="text-xs text-red-500 py-4">Lỗi tải sổ điểm: ${escapeHtml(e.message)}</p>`;
  }
}

// ================= VIEW 4: ADMIN PORTAL (QT ONLY) =================
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

// ================= MODAL SUBMITS & FORM HANDLERS =================
async function handleLoginSubmit(e) {
  e.preventDefault();
  const email = document.getElementById('login-email').value;
  const password = document.getElementById('login-password').value;

  try {
    const res = await api('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    setSession(res);
    showToast('Đăng nhập thành công!', 'success');
    closeModal('modal-login');
    await initApp();
  } catch (err) {
    console.error(err);
  }
}

async function handleRegisterSubmit(e) {
  e.preventDefault();
  const full_name = document.getElementById('reg-fullname').value;
  const email = document.getElementById('reg-email').value;
  const password = document.getElementById('reg-password').value;

  try {
    const res = await api('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify({ full_name, email, password }),
    });
    showToast(res.message, 'success');
    closeModal('modal-register');
    openLoginModal();
  } catch (err) {
    console.error(err);
  }
}

async function handleEnrollSubmit(e) {
  e.preventDefault();
  const code = document.getElementById('enroll-course-code').value.trim();
  if (!code) return;

  try {
    const res = await api('/api/courses/enroll', {
      method: 'POST',
      body: JSON.stringify({ course_code: code }),
    });
    showToast(res.message, 'success');
    closeModal('modal-enroll');
    loadCourses();
  } catch (err) {
    console.error(err);
  }
}

async function handleCreateCourseSubmit(e) {
  e.preventDefault();
  const code = document.getElementById('new-course-code').value.trim().toUpperCase();
  const title = document.getElementById('new-course-title').value.trim();
  const description = document.getElementById('new-course-desc').value.trim();

  try {
    await api('/api/courses', {
      method: 'POST',
      body: JSON.stringify({ code, title, description }),
    });
    showToast(`Khởi tạo khóa học ${code} thành công!`, 'success');
    closeModal('modal-create-course');
    loadCourses();
  } catch (err) {
    console.error(err);
  }
}

async function handleUploadMaterialSubmit(e) {
  e.preventDefault();
  if (!state.currentCourse) return;

  const title = document.getElementById('material-title').value.trim();
  const fileInput = document.getElementById('material-file');
  if (!fileInput.files || fileInput.files.length === 0) return;

  const formData = new FormData();
  formData.append('title', title);
  formData.append('file', fileInput.files[0]);

  try {
    await api(`/api/courses/${state.currentCourse.id}/materials`, {
      method: 'POST',
      body: formData,
    });
    showToast('Tải lên tài liệu thành công!', 'success');
    closeModal('modal-upload-material');
    loadCourseMaterials();
  } catch (err) {
    console.error(err);
  }
}

async function handleCreateAssignmentSubmit(e) {
  e.preventDefault();
  if (!state.currentCourse) return;

  const title = document.getElementById('assign-title').value.trim();
  const description = document.getElementById('assign-desc').value.trim();
  const deadlineVal = document.getElementById('assign-deadline').value;
  const max_score = parseFloat(document.getElementById('assign-max-score').value);

  const deadline = new Date(deadlineVal).toISOString();

  try {
    await api(`/api/courses/${state.currentCourse.id}/assignments`, {
      method: 'POST',
      body: JSON.stringify({ title, description, deadline, max_score }),
    });
    showToast('Giao bài tập mới thành công!', 'success');
    closeModal('modal-create-assignment');
    loadCourseAssignments();
  } catch (err) {
    console.error(err);
  }
}

async function handleStudentSubmitAssignment(e) {
  e.preventDefault();
  if (!state.activeAssignment) return;

  const fileInput = document.getElementById('submit-file');
  if (!fileInput.files || fileInput.files.length === 0) {
    showToast('Vui lòng chọn tệp bài làm trước khi nộp', 'warning');
    return;
  }

  const formData = new FormData();
  formData.append('file', fileInput.files[0]);

  try {
    await api(`/api/assignments/${state.activeAssignment.id}/submit`, {
      method: 'POST',
      body: formData,
    });
    showToast('Nộp bài tập thành công!', 'success');
    loadStudentSubmission(state.activeAssignment.id);
  } catch (err) {
    console.error(err);
  }
}

async function handleCreateAnnouncementSubmit(e) {
  e.preventDefault();
  if (!state.currentCourse) return;

  const title = document.getElementById('announce-title').value.trim();
  const content = document.getElementById('announce-content').value.trim();

  try {
    await api(`/api/courses/${state.currentCourse.id}/announcements`, {
      method: 'POST',
      body: JSON.stringify({ title, content }),
    });
    showToast('Đã phát hành thông báo tới toàn thể sinh viên!', 'success');
    closeModal('modal-create-announcement');
    loadCourseForumAndAnnouncements();
  } catch (err) {
    console.error(err);
  }
}

async function handleCreateTopicSubmit(e) {
  e.preventDefault();
  if (!state.currentCourse) return;

  const title = document.getElementById('topic-title').value.trim();
  const content = document.getElementById('topic-content').value.trim();

  try {
    await api(`/api/courses/${state.currentCourse.id}/topics`, {
      method: 'POST',
      body: JSON.stringify({ title, content }),
    });
    showToast('Đã tạo chủ đề thảo luận mới!', 'success');
    closeModal('modal-create-topic');
    loadCourseForumAndAnnouncements();
  } catch (err) {
    console.error(err);
  }
}

async function handlePostCommentSubmit(e) {
  e.preventDefault();
  if (!state.activeTopic) return;

  const input = document.getElementById('new-comment-content');
  const content = input.value.trim();
  if (!content) return;

  try {
    const comment = await api(`/api/topics/${state.activeTopic.id}/comments`, {
      method: 'POST',
      body: JSON.stringify({ content }),
    });
    input.value = '';
    state.activeTopic.comments = state.activeTopic.comments || [];
    state.activeTopic.comments.push(comment);
    document.getElementById('modal-topic-comment-count').textContent = state.activeTopic.comments.length;
    renderTopicComments(state.activeTopic.comments);
    showToast('Đã gửi bình luận.', 'success');
  } catch (err) {
    console.error(err);
  }
}

// Question Builder Helper
let questionCounter = 0;
function addQuizQuestionBuilder() {
  questionCounter++;
  const qId = questionCounter;
  const container = document.getElementById('quiz-questions-builder');

  const div = document.createElement('div');
  div.id = `q-builder-${qId}`;
  div.className = 'p-3 rounded-xl border border-slate-200 bg-slate-50 space-y-2 text-xs';
  div.innerHTML = `
    <div class="flex items-center justify-between">
      <span class="font-bold text-slate-800">Câu hỏi #${qId}</span>
      <button type="button" onclick="document.getElementById('q-builder-${qId}').remove()" class="text-red-500 hover:text-red-700">Xóa</button>
    </div>
    <div>
      <input type="text" placeholder="Nội dung câu hỏi..." class="q-content w-full px-2.5 py-1.5 border rounded-lg bg-white" required>
    </div>
    <div class="space-y-1.5 pl-2 border-l-2 border-indigo-200">
      <span class="text-[10px] text-slate-500 font-semibold uppercase">Các lựa chọn (Tích tròn đáp án đúng):</span>
      ${[1, 2, 3, 4].map(optIdx => `
        <div class="flex items-center space-x-2">
          <input type="radio" name="correct_opt_${qId}" value="${optIdx}" ${optIdx === 1 ? 'checked' : ''} class="text-indigo-600">
          <input type="text" placeholder="Đáp án ${optIdx}..." class="opt-content-${optIdx} flex-1 px-2 py-1 border rounded bg-white" required>
        </div>
      `).join('')}
    </div>
  `;
  container.appendChild(div);
}

async function handleCreateQuizSubmit(e) {
  e.preventDefault();
  if (!state.currentCourse) return;

  const title = document.getElementById('quiz-title').value.trim();
  const description = document.getElementById('quiz-desc').value.trim();
  const time_limit_minutes = parseInt(document.getElementById('quiz-time-limit').value);

  const qElements = document.querySelectorAll('#quiz-questions-builder > div');
  if (qElements.length === 0) {
    showToast('Vui lòng thêm ít nhất 1 câu hỏi cho đề thi!', 'warning');
    return;
  }

  const questions = [];
  qElements.forEach(el => {
    const content = el.querySelector('.q-content').value.trim();
    const correctRadio = el.querySelector('input[type="radio"]:checked');
    const correctVal = correctRadio ? parseInt(correctRadio.value) : 1;

    const options = [];
    for (let i = 1; i <= 4; i++) {
      const optInput = el.querySelector(`.opt-content-${i}`);
      if (optInput && optInput.value.trim()) {
        options.push({
          content: optInput.value.trim(),
          is_correct: i === correctVal,
        });
      }
    }

    questions.push({
      content,
      points: 2.5,
      options,
    });
  });

  try {
    await api(`/api/courses/${state.currentCourse.id}/quizzes`, {
      method: 'POST',
      body: JSON.stringify({
        title,
        description,
        time_limit_minutes,
        max_attempts: 3,
        questions,
      }),
    });
    showToast(`Đã xuất bản bài trắc nghiệm '${title}' thành công!`, 'success');
    closeModal('modal-create-quiz');
    loadCourseQuizzes();
  } catch (err) {
    console.error(err);
  }
}

async function handleUpdateProfileSubmit(e) {
  e.preventDefault();
  const full_name = document.getElementById('prof-fullname').value.trim();
  const bio = document.getElementById('prof-bio').value.trim();
  const contact_info = document.getElementById('prof-contact').value.trim();

  try {
    const res = await api('/api/users/me', {
      method: 'PUT',
      body: JSON.stringify({ full_name, bio, contact_info }),
    });
    state.currentUser.full_name = res.full_name;
    localStorage.setItem('lms_user', JSON.stringify(state.currentUser));
    updateNavState();
    showToast('Cập nhật hồ sơ cá nhân thành công!', 'success');
    closeModal('modal-profile');
  } catch (err) {
    console.error(err);
  }
}

async function handleChangePasswordSubmit(e) {
  e.preventDefault();
  const old_password = document.getElementById('chg-old-password').value;
  const new_password = document.getElementById('chg-new-password').value;

  try {
    const res = await api('/api/auth/change-password', {
      method: 'POST',
      body: JSON.stringify({ old_password, new_password }),
    });
    showToast(res.message, 'success');
    closeModal('modal-change-password');
  } catch (err) {
    console.error(err);
  }
}

async function handleForgotPasswordSubmit(e) {
  e.preventDefault();
  const email = document.getElementById('forgot-email').value.trim();

  try {
    const res = await api('/api/auth/forgot-password', {
      method: 'POST',
      body: JSON.stringify({ email }),
    });
    showToast(res.message, 'info');
    closeModal('modal-forgot-password');
  } catch (err) {
    console.error(err);
  }
}

// ================= MODAL CONTROLS =================
function openModal(id) {
  document.getElementById(id)?.classList.remove('hidden');
}

function closeModal(id) {
  document.getElementById(id)?.classList.add('hidden');
}

function closeAllModals() {
  document.querySelectorAll('[id^="modal-"]').forEach(m => m.classList.add('hidden'));
}

function openLoginModal() { openModal('modal-login'); }
function openRegisterModal() { openModal('modal-register'); }
function openEnrollModal() { openModal('modal-enroll'); }
function openCreateCourseModal() { openModal('modal-create-course'); }
function openUploadMaterialModal() { openModal('modal-upload-material'); }
function openCreateAssignmentModal() { openModal('modal-create-assignment'); }
function openCreateAnnouncementModal() { openModal('modal-create-announcement'); }
function openCreateTopicModal() { openModal('modal-create-topic'); }
function openChangePasswordModal() { openModal('modal-change-password'); }
function openForgotPasswordModal() { closeModal('modal-login'); openModal('modal-forgot-password'); }

function openCreateQuizModal() {
  const container = document.getElementById('quiz-questions-builder');
  container.innerHTML = '';
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
  if (typeof forceState === 'boolean') {
    if (forceState) menu.classList.remove('hidden');
    else menu.classList.add('hidden');
  } else {
    menu.classList.toggle('hidden');
  }
}

// ================= UTILITIES =================
function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function formatDate(isoStr) {
  if (!isoStr) return '';
  try {
    const d = new Date(isoStr);
    return d.toLocaleString('vi-VN', {
      hour: '2-digit',
      minute: '2-digit',
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
    });
  } catch {
    return isoStr;
  }
}

// Close user dropdown when clicking outside
document.addEventListener('click', (e) => {
  const dropdown = document.getElementById('user-dropdown');
  const userButton = e.target.closest('#user-logged-in button');
  if (!userButton && dropdown && !dropdown.contains(e.target)) {
    dropdown.classList.add('hidden');
  }
});

// ================= INITIALIZATION =================
async function initApp() {
  updateNavState();
  if (state.token) {
    try {
      const me = await api('/api/users/me');
      state.currentUser = me;
      localStorage.setItem('lms_user', JSON.stringify(me));
      updateNavState();
    } catch {
      logout(false);
    }
  } else {
    // If not logged in on first visit, automatically quick-login as student for instant delight
    quickLogin('student1@lms.edu.vn', 'student123');
    return;
  }

  loadCourses();
}

window.addEventListener('DOMContentLoaded', () => {
  initApp();
});
