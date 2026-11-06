/**
 * MiniLMS - Course Gradebook & Personal Grades Module
 */

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

async function loadMyGrades() {
  const container = document.getElementById('my-grades-table-container');
  container.innerHTML = `<div class="py-8 text-center text-slate-400 text-xs"><i class="fa-solid fa-spinner fa-spin mr-1"></i> Đang tải sổ điểm cá nhân...</div>`;

  try {
    const res = await api('/api/my-grades');
    const subs = Array.isArray(res) ? res : (res.courses || []);
    if (subs.length === 0) {
      container.innerHTML = `<p class="py-8 text-center text-slate-400 text-xs">Chưa có bài tập nào được chấm điểm.</p>`;
      return;
    }

    if (Array.isArray(res)) {
      container.innerHTML = `
        <table class="w-full text-left text-xs">
          <thead class="bg-slate-50 text-slate-500 uppercase font-semibold border-y border-slate-100">
            <tr>
              <th class="py-2.5 px-4">Mã Bài tập</th>
              <th class="py-2.5 px-4">Tệp đã nộp</th>
              <th class="py-2.5 px-4">Ngày nộp</th>
              <th class="py-2.5 px-4">Điểm số</th>
              <th class="py-2.5 px-4">Nhận xét của Giảng viên</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            ${res.map(s => `
              <tr class="hover:bg-slate-50/50">
                <td class="py-2.5 px-4 font-mono font-bold text-slate-700">#${s.assignment_id}</td>
                <td class="py-2.5 px-4 font-semibold text-slate-800">${escapeHtml(s.filename)}</td>
                <td class="py-2.5 px-4 text-slate-500">${formatDate(s.submitted_at)}</td>
                <td class="py-2.5 px-4 font-bold text-emerald-700">${s.score !== null ? s.score : '-'}</td>
                <td class="py-2.5 px-4 text-slate-600 italic">${escapeHtml(s.feedback || '-')}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      `;
    }
  } catch (e) {
    container.innerHTML = `<p class="text-xs text-red-500 py-4">Lỗi tải sổ điểm: ${escapeHtml(e.message)}</p>`;
  }
}
