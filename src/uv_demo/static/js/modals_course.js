/**
 * MiniLMS - Course, Material & Assignment Modal Templates
 */
(function injectCourseModals() {
  const container = document.getElementById('modals-container');
  if (!container) return;

  container.insertAdjacentHTML('beforeend', `
  <!-- 1. ENROLL MODAL (SV) -->
  <div id="modal-enroll" class="hidden fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
    <div class="bg-white rounded-2xl max-w-sm w-full p-6 shadow-2xl border border-slate-200 space-y-4">
      <div class="flex items-center justify-between">
        <h3 class="text-base font-bold text-slate-900">Ghi Danh Bằng Mã Khóa Học</h3>
        <button onclick="closeModal('modal-enroll')" class="text-slate-400 hover:text-slate-600"><i class="fa-solid fa-xmark"></i></button>
      </div>
      <form onsubmit="handleEnrollSubmit(event)" class="space-y-3">
        <div>
          <label class="block text-xs font-semibold text-slate-700 mb-1">Mã khóa học (Ví dụ: CS101, CS202)</label>
          <input type="text" id="enroll-course-code" required placeholder="CS101" class="uppercase w-full px-3 py-2 text-sm font-mono border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-sky-500">
        </div>
        <button type="submit" class="w-full py-2.5 rounded-xl bg-sky-600 hover:bg-sky-700 text-white font-semibold text-sm transition shadow-md shadow-sky-200">
          Ghi danh ngay
        </button>
      </form>
    </div>
  </div>

  <!-- 2. CREATE COURSE MODAL (GV / QT) -->
  <div id="modal-create-course" class="hidden fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
    <div class="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-slate-200 space-y-4">
      <div class="flex items-center justify-between">
        <h3 class="text-lg font-bold text-slate-900">Tạo Khóa Học Mới</h3>
        <button onclick="closeModal('modal-create-course')" class="text-slate-400 hover:text-slate-600"><i class="fa-solid fa-xmark"></i></button>
      </div>
      <form onsubmit="handleCreateCourseSubmit(event)" class="space-y-3">
        <div class="grid grid-cols-3 gap-3">
          <div>
            <label class="block text-xs font-semibold text-slate-700 mb-1">Mã môn học</label>
            <input type="text" id="new-course-code" required placeholder="CS303" class="uppercase w-full px-3 py-2 text-sm font-mono border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500">
          </div>
          <div class="col-span-2">
            <label class="block text-xs font-semibold text-slate-700 mb-1">Tên khóa học</label>
            <input type="text" id="new-course-title" required placeholder="Lập trình Web An toàn" class="w-full px-3 py-2 text-sm border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500">
          </div>
        </div>
        <div>
          <label class="block text-xs font-semibold text-slate-700 mb-1">Mô tả khóa học</label>
          <textarea id="new-course-desc" rows="3" placeholder="Nội dung, mục tiêu và yêu cầu tiên quyết của môn học..." class="w-full px-3 py-2 text-sm border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500"></textarea>
        </div>
        <button type="submit" class="w-full py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-sm transition shadow-md shadow-indigo-200">
          Lưu & Khởi tạo Khóa học
        </button>
      </form>
    </div>
  </div>

  <!-- 3. UPLOAD MATERIAL MODAL (GV / QT) -->
  <div id="modal-upload-material" class="hidden fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
    <div class="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-slate-200 space-y-4">
      <div class="flex items-center justify-between">
        <h3 class="text-base font-bold text-slate-900">Tải Lên Tài Liệu Bài Giảng</h3>
        <button onclick="closeModal('modal-upload-material')" class="text-slate-400 hover:text-slate-600"><i class="fa-solid fa-xmark"></i></button>
      </div>
      <form onsubmit="handleUploadMaterialSubmit(event)" class="space-y-3">
        <div>
          <label class="block text-xs font-semibold text-slate-700 mb-1">Tiêu đề tài liệu</label>
          <input type="text" id="material-title" required placeholder="Giáo trình Tuần 1: Nhập môn" class="w-full px-3 py-2 text-sm border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500">
        </div>
        <div>
          <label class="block text-xs font-semibold text-slate-700 mb-1">Chọn tệp (.pdf, .docx, .zip, .pptx)</label>
          <input type="file" id="material-file" required class="w-full text-xs text-slate-500 file:mr-3 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-xs file:font-semibold file:bg-emerald-50 file:text-emerald-700 hover:file:bg-emerald-100">
        </div>
        <button type="submit" class="w-full py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-semibold text-sm transition shadow-md shadow-emerald-200">
          Tải lên ngay
        </button>
      </form>
    </div>
  </div>

  <!-- 4. CREATE ASSIGNMENT MODAL (GV / QT) -->
  <div id="modal-create-assignment" class="hidden fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
    <div class="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-slate-200 space-y-4">
      <div class="flex items-center justify-between">
        <h3 class="text-lg font-bold text-slate-900">Giao Bài Tập Mới</h3>
        <button onclick="closeModal('modal-create-assignment')" class="text-slate-400 hover:text-slate-600"><i class="fa-solid fa-xmark"></i></button>
      </div>
      <form onsubmit="handleCreateAssignmentSubmit(event)" class="space-y-3">
        <div>
          <label class="block text-xs font-semibold text-slate-700 mb-1">Tiêu đề bài tập</label>
          <input type="text" id="assign-title" required placeholder="Bài tập 2: Thiết kế Database & Unit Tests" class="w-full px-3 py-2 text-sm border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500">
        </div>
        <div>
          <label class="block text-xs font-semibold text-slate-700 mb-1">Mô tả & Hướng dẫn làm bài</label>
          <textarea id="assign-desc" rows="3" required placeholder="Yêu cầu sinh viên hoàn thành file mã nguồn..." class="w-full px-3 py-2 text-sm border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500"></textarea>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="block text-xs font-semibold text-slate-700 mb-1">Hạn nộp (Deadline)</label>
            <input type="datetime-local" id="assign-deadline" required class="w-full px-3 py-2 text-xs border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500">
          </div>
          <div>
            <label class="block text-xs font-semibold text-slate-700 mb-1">Thang điểm tối đa</label>
            <input type="number" id="assign-max-score" min="1" max="100" value="10" step="0.5" required class="w-full px-3 py-2 text-sm border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500">
          </div>
        </div>
        <button type="submit" class="w-full py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-sm transition shadow-md shadow-indigo-200">
          Phát hành Bài tập
        </button>
      </form>
    </div>
  </div>

  <!-- 5. ASSIGNMENT DETAIL & SUBMISSION / GRADING MODAL -->
  <div id="modal-assignment-detail" class="hidden fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
    <div class="bg-white rounded-2xl max-w-2xl w-full p-6 shadow-2xl border border-slate-200 space-y-4 max-h-[90vh] overflow-y-auto custom-scroll">
      <div class="flex items-center justify-between border-b border-slate-100 pb-3">
        <div>
          <span class="text-[11px] font-semibold text-indigo-600 uppercase tracking-wider">Chi tiết bài tập</span>
          <h3 id="modal-assign-title" class="text-lg font-bold text-slate-900">Tiêu đề bài tập</h3>
        </div>
        <button onclick="closeModal('modal-assignment-detail')" class="text-slate-400 hover:text-slate-600"><i class="fa-solid fa-xmark"></i></button>
      </div>
      <div class="space-y-2 text-sm">
        <p id="modal-assign-desc" class="text-slate-600 bg-slate-50 p-3 rounded-xl border border-slate-200/60 leading-relaxed"></p>
        <div class="flex items-center space-x-4 text-xs text-slate-500">
          <span><i class="fa-regular fa-clock mr-1 text-slate-400"></i> Hạn chót: <b id="modal-assign-deadline" class="text-slate-700"></b></span>
          <span><i class="fa-solid fa-star mr-1 text-amber-500"></i> Điểm tối đa: <b id="modal-assign-max-score" class="text-slate-700"></b></span>
        </div>
      </div>
      <div id="assign-student-view" class="hidden space-y-3 pt-3 border-t border-slate-100">
        <h4 class="text-sm font-bold text-slate-900 flex items-center">
          <i class="fa-solid fa-paper-plane mr-2 text-sky-600"></i> Bài Nộp Của Bạn
        </h4>
        <div id="student-submission-status" class="p-4 rounded-xl border"></div>
        <form id="form-submit-assignment" onsubmit="handleStudentSubmitAssignment(event)" class="space-y-3">
          <div>
            <label class="block text-xs font-semibold text-slate-700 mb-1">Tải lên tệp bài làm (.zip, .pdf, .docx, .py)</label>
            <input type="file" id="submit-file" required class="w-full text-xs text-slate-500 file:mr-3 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-xs file:font-semibold file:bg-sky-50 file:text-sky-700 hover:file:bg-sky-100">
          </div>
          <button type="submit" class="px-4 py-2 rounded-xl bg-sky-600 hover:bg-sky-700 text-white font-semibold text-xs transition shadow-sm">
            Nộp bài tập
          </button>
        </form>
      </div>
      <div id="assign-teacher-view" class="hidden space-y-3 pt-3 border-t border-slate-100">
        <h4 class="text-sm font-bold text-slate-900 flex items-center">
          <i class="fa-solid fa-list-check mr-2 text-emerald-600"></i> Danh Sách Bài Nộp Của Sinh Viên
        </h4>
        <div class="overflow-x-auto">
          <table class="w-full text-left text-xs">
            <thead class="bg-slate-50 text-slate-500 uppercase font-semibold border-y border-slate-100">
              <tr>
                <th class="py-2.5 px-3">Sinh viên</th>
                <th class="py-2.5 px-3">Tệp nộp</th>
                <th class="py-2.5 px-3">Thời gian</th>
                <th class="py-2.5 px-3">Điểm số</th>
                <th class="py-2.5 px-3">Nhận xét</th>
                <th class="py-2.5 px-3 text-right">Lưu điểm</th>
              </tr>
            </thead>
            <tbody id="assign-submissions-table" class="divide-y divide-slate-100"></tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
  `);
})();
