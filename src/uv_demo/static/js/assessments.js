/**
 * MiniLMS - Assignments, Submissions, Grading & Quizzes Module
 */

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
      method: 'PUT',
      body: JSON.stringify({ score, feedback }),
    });
    showToast('Đã lưu điểm và nhận xét thành công!', 'success');
    if (state.activeAssignment) loadTeacherSubmissionsList(state.activeAssignment.id);
  } catch (e) {
    showToast('Không thể lưu điểm: ' + e.message, 'error');
  }
}

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
          <span class="text-xs text-slate-500">Tối đa: ${q.max_attempts || 3} lần nộp</span>
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
