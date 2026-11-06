/**
 * MiniLMS - Courses Catalog, Course Detail, Forum, Materials & Members Module
 */

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

async function openCourseDetail(courseId) {
  try {
    const course = await api(`/api/courses/${courseId}`);
    state.currentCourse = course;

    document.getElementById('detail-course-code').textContent = course.code;
    document.getElementById('detail-course-title').textContent = course.title;
    document.getElementById('detail-course-desc').textContent = course.description || 'Chưa có mô tả chi tiết.';
    document.getElementById('detail-course-instructor').textContent = course.instructor_name || 'Giảng viên';

    const isInstructorOrAdmin = state.currentUser && (
      state.currentUser.role === 'QT' ||
      (state.currentUser.role === 'GV' && course.instructor_id === state.currentUser.id)
    );

    const ids = [
      'btn-open-create-announcement',
      'btn-open-upload-material',
      'btn-open-create-assignment',
      'btn-open-create-quiz',
      'instructor-add-student-box',
    ];
    ids.forEach(id => {
      const el = document.getElementById(id);
      if (el) el.classList.toggle('hidden', !isInstructorOrAdmin);
    });

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
    document.getElementById(`pane-${t}`)?.classList.add('hidden');
    const btn = document.getElementById(`subtab-${t}`);
    if (btn) {
      btn.classList.remove('text-indigo-600', 'bg-indigo-50');
      btn.classList.add('text-slate-600');
    }
  });

  document.getElementById(`pane-${tabName}`)?.classList.remove('hidden');
  const activeBtn = document.getElementById(`subtab-${tabName}`);
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

async function loadCourseForumAndAnnouncements() {
  if (!state.currentCourse) return;
  const courseId = state.currentCourse.id;

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

  const topicList = document.getElementById('topics-list');
  try {
    const topics = await api(`/api/courses/${courseId}/topics`);
    if (topics.length === 0) {
      topicList.innerHTML = `<div class="py-8 text-center text-slate-400 text-xs">Chưa có chủ đề thảo luận nào. Hãy là người đầu tiên đặt câu hỏi!</div>`;
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
