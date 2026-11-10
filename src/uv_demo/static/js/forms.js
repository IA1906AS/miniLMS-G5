/**
 * MiniLMS - Form Submission & Quiz Builder Handlers Module
 */

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

  const selectedFile = fileInput.files[0];
  const idempotencyKey = `sub-${state.activeAssignment.id}-${selectedFile.name}-${selectedFile.size}-${selectedFile.lastModified}`;
  const formData = new FormData();
  formData.append('file', selectedFile);

  try {
    await api(`/api/assignments/${state.activeAssignment.id}/submit`, {
      method: 'POST',
      headers: { 'Idempotency-Key': idempotencyKey },
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
    questions.push({ content, points: 2.5, options });
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
