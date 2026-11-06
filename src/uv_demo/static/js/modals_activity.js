/**
 * MiniLMS - Quiz, Forum, Announcement & Profile Modal Templates
 */
(function injectActivityModals() {
  const container = document.getElementById('modals-container');
  if (!container) return;

  container.insertAdjacentHTML('beforeend', `
  <!-- 6. CREATE QUIZ MODAL (GV / QT) -->
  <div id="modal-create-quiz" class="hidden fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
    <div class="bg-white rounded-2xl max-w-2xl w-full p-6 shadow-2xl border border-slate-200 space-y-4 max-h-[90vh] overflow-y-auto custom-scroll">
      <div class="flex items-center justify-between border-b border-slate-100 pb-3">
        <h3 class="text-lg font-bold text-slate-900">Soạn Bài Kiểm Tra Trắc Nghiệm</h3>
        <button onclick="closeModal('modal-create-quiz')" class="text-slate-400 hover:text-slate-600"><i class="fa-solid fa-xmark"></i></button>
      </div>
      <form onsubmit="handleCreateQuizSubmit(event)" class="space-y-4">
        <div class="grid grid-cols-3 gap-3">
          <div class="col-span-2">
            <label class="block text-xs font-semibold text-slate-700 mb-1">Tiêu đề bài trắc nghiệm</label>
            <input type="text" id="quiz-title" required placeholder="Kiểm tra kiến thức Python 3.12" class="w-full px-3 py-2 text-sm border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500">
          </div>
          <div>
            <label class="block text-xs font-semibold text-slate-700 mb-1">Thời gian (phút)</label>
            <input type="number" id="quiz-time-limit" min="1" max="180" value="15" required class="w-full px-3 py-2 text-sm border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500">
          </div>
        </div>
        <div>
          <label class="block text-xs font-semibold text-slate-700 mb-1">Mô tả đề thi</label>
          <input type="text" id="quiz-desc" placeholder="Gồm các câu hỏi trắc nghiệm tự động chấm..." class="w-full px-3 py-2 text-sm border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500">
        </div>
        <div class="space-y-3 pt-2">
          <div class="flex items-center justify-between">
            <label class="text-xs font-bold text-slate-800 uppercase tracking-wider">Danh Sách Câu Hỏi</label>
            <button type="button" onclick="addQuizQuestionBuilder()" class="px-2.5 py-1 text-xs font-semibold bg-indigo-50 text-indigo-700 hover:bg-indigo-100 rounded-lg transition">
              + Thêm câu hỏi
            </button>
          </div>
          <div id="quiz-questions-builder" class="space-y-4"></div>
        </div>
        <button type="submit" class="w-full py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-sm transition shadow-md shadow-indigo-200">
          Xuất bản Đề kiểm tra
        </button>
      </form>
    </div>
  </div>

  <!-- 7. TAKE QUIZ MODAL (SV) -->
  <div id="modal-take-quiz" class="hidden fixed inset-0 bg-slate-900/60 backdrop-blur-md z-50 flex items-center justify-center p-4">
    <div class="bg-white rounded-2xl max-w-2xl w-full p-6 shadow-2xl border border-slate-200 space-y-4 max-h-[95vh] flex flex-col">
      <div class="flex items-center justify-between border-b border-slate-100 pb-3">
        <div>
          <span class="text-xs font-semibold text-indigo-600 uppercase">Đang làm bài trắc nghiệm</span>
          <h3 id="take-quiz-title" class="text-lg font-bold text-slate-900">Tiêu đề bài kiểm tra</h3>
        </div>
        <div class="flex items-center space-x-2 bg-red-50 text-red-600 px-3.5 py-1.5 rounded-xl border border-red-200 font-mono font-bold text-sm">
          <i class="fa-solid fa-stopwatch animate-pulse"></i>
          <span id="quiz-countdown-timer">15:00</span>
        </div>
      </div>
      <div id="take-quiz-questions" class="flex-1 overflow-y-auto custom-scroll space-y-6 py-2"></div>
      <div class="pt-3 border-t border-slate-100 flex items-center justify-between">
        <span class="text-xs text-slate-500"><i class="fa-solid fa-shield-cat mr-1 text-indigo-500"></i> Bài thi tự động lưu và chấm điểm khi nộp</span>
        <button onclick="submitQuizAnswers()" class="px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-sm transition shadow-md shadow-indigo-200">
          Nộp Bài Kiểm Tra
        </button>
      </div>
    </div>
  </div>

  <!-- 8. CREATE FORUM TOPIC MODAL -->
  <div id="modal-create-topic" class="hidden fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
    <div class="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-slate-200 space-y-4">
      <div class="flex items-center justify-between">
        <h3 class="text-base font-bold text-slate-900">Đăng Chủ Đề Thảo Luận Mới</h3>
        <button onclick="closeModal('modal-create-topic')" class="text-slate-400 hover:text-slate-600"><i class="fa-solid fa-xmark"></i></button>
      </div>
      <form onsubmit="handleCreateTopicSubmit(event)" class="space-y-3">
        <div>
          <label class="block text-xs font-semibold text-slate-700 mb-1">Tiêu đề chủ đề</label>
          <input type="text" id="topic-title" required placeholder="Thắc mắc về bài học..." class="w-full px-3 py-2 text-sm border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500">
        </div>
        <div>
          <label class="block text-xs font-semibold text-slate-700 mb-1">Nội dung chi tiết</label>
          <textarea id="topic-content" rows="4" required placeholder="Mô tả câu hỏi hoặc nội dung bạn muốn trao đổi..." class="w-full px-3 py-2 text-sm border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500"></textarea>
        </div>
        <button type="submit" class="w-full py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-sm transition shadow-md shadow-indigo-200">
          Đăng bài thảo luận
        </button>
      </form>
    </div>
  </div>

  <!-- 9. CREATE ANNOUNCEMENT MODAL (GV / QT) -->
  <div id="modal-create-announcement" class="hidden fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
    <div class="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-slate-200 space-y-4">
      <div class="flex items-center justify-between">
        <h3 class="text-base font-bold text-slate-900">Tạo Thông Báo Mới</h3>
        <button onclick="closeModal('modal-create-announcement')" class="text-slate-400 hover:text-slate-600"><i class="fa-solid fa-xmark"></i></button>
      </div>
      <form onsubmit="handleCreateAnnouncementSubmit(event)" class="space-y-3">
        <div>
          <label class="block text-xs font-semibold text-slate-700 mb-1">Tiêu đề thông báo</label>
          <input type="text" id="announce-title" required placeholder="Lịch thi giữa kỳ môn học..." class="w-full px-3 py-2 text-sm border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-amber-500">
        </div>
        <div>
          <label class="block text-xs font-semibold text-slate-700 mb-1">Nội dung thông báo</label>
          <textarea id="announce-content" rows="4" required placeholder="Các em lưu ý kiểm tra lịch thi và chuẩn bị bài tập..." class="w-full px-3 py-2 text-sm border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-amber-500"></textarea>
        </div>
        <button type="submit" class="w-full py-2.5 rounded-xl bg-amber-600 hover:bg-amber-700 text-white font-semibold text-sm transition shadow-md shadow-amber-200">
          Gửi Thông Báo (Tự động gửi email)
        </button>
      </form>
    </div>
  </div>

  <!-- 10. FORUM TOPIC DETAIL & COMMENTS MODAL -->
  <div id="modal-topic-detail" class="hidden fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
    <div class="bg-white rounded-2xl max-w-2xl w-full p-6 shadow-2xl border border-slate-200 space-y-4 max-h-[90vh] overflow-y-auto custom-scroll">
      <div class="flex items-center justify-between border-b border-slate-100 pb-3">
        <div>
          <span class="text-xs text-indigo-600 font-semibold uppercase">Thảo luận môn học</span>
          <h3 id="modal-topic-title" class="text-lg font-bold text-slate-900">Tiêu đề chủ đề</h3>
          <div class="text-xs text-slate-400 mt-0.5">Người đăng: <span id="modal-topic-author" class="font-medium text-slate-700"></span> • <span id="modal-topic-time"></span></div>
        </div>
        <button onclick="closeModal('modal-topic-detail')" class="text-slate-400 hover:text-slate-600"><i class="fa-solid fa-xmark"></i></button>
      </div>
      <div id="modal-topic-content" class="text-sm text-slate-700 bg-slate-50 p-4 rounded-xl border border-slate-200/60 leading-relaxed whitespace-pre-wrap"></div>
      <div class="space-y-3 pt-2">
        <h4 class="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center">
          <i class="fa-solid fa-comments mr-2 text-indigo-600"></i> Bình Luận (<span id="modal-topic-comment-count">0</span>)
        </h4>
        <div id="modal-topic-comments" class="space-y-2.5"></div>
        <form onsubmit="handlePostCommentSubmit(event)" class="pt-2 flex items-center space-x-2">
          <input type="text" id="new-comment-content" required placeholder="Viết phản hồi bình luận của bạn..." class="flex-1 px-3 py-2 text-xs border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500">
          <button type="submit" class="px-4 py-2 text-xs font-semibold bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl transition shadow-sm">
            Gửi
          </button>
        </form>
      </div>
    </div>
  </div>

  <!-- 11. USER PROFILE MODAL -->
  <div id="modal-profile" class="hidden fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
    <div class="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-slate-200 space-y-4">
      <div class="flex items-center justify-between">
        <h3 class="text-lg font-bold text-slate-900">Hồ Sơ Cá Nhân</h3>
        <button onclick="closeModal('modal-profile')" class="text-slate-400 hover:text-slate-600"><i class="fa-solid fa-xmark"></i></button>
      </div>
      <form onsubmit="handleUpdateProfileSubmit(event)" class="space-y-3">
        <div>
          <label class="block text-xs font-semibold text-slate-700 mb-1">Họ và tên</label>
          <input type="text" id="prof-fullname" required class="w-full px-3 py-2 text-sm border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500">
        </div>
        <div>
          <label class="block text-xs font-semibold text-slate-700 mb-1">Email (Chỉ xem)</label>
          <input type="email" id="prof-email" disabled class="w-full px-3 py-2 text-sm bg-slate-100 text-slate-500 border border-slate-200 rounded-xl cursor-not-allowed">
        </div>
        <div>
          <label class="block text-xs font-semibold text-slate-700 mb-1">Vai trò hệ thống</label>
          <input type="text" id="prof-role" disabled class="w-full px-3 py-2 text-sm bg-slate-100 font-semibold border border-slate-200 rounded-xl cursor-not-allowed">
        </div>
        <div>
          <label class="block text-xs font-semibold text-slate-700 mb-1">Giới thiệu bản thân (Bio)</label>
          <textarea id="prof-bio" rows="2" placeholder="Sở thích, chuyên ngành..." class="w-full px-3 py-2 text-sm border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500"></textarea>
        </div>
        <div>
          <label class="block text-xs font-semibold text-slate-700 mb-1">Thông tin liên hệ</label>
          <input type="text" id="prof-contact" placeholder="Số điện thoại hoặc link GitHub" class="w-full px-3 py-2 text-sm border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500">
        </div>
        <button type="submit" class="w-full py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-sm transition shadow-md shadow-indigo-200">
          Cập nhật Hồ sơ
        </button>
      </form>
    </div>
  </div>

  <!-- 12. CHANGE PASSWORD MODAL -->
  <div id="modal-change-password" class="hidden fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
    <div class="bg-white rounded-2xl max-w-sm w-full p-6 shadow-2xl border border-slate-200 space-y-4">
      <div class="flex items-center justify-between">
        <h3 class="text-base font-bold text-slate-900">Đổi Mật Khẩu</h3>
        <button onclick="closeModal('modal-change-password')" class="text-slate-400 hover:text-slate-600"><i class="fa-solid fa-xmark"></i></button>
      </div>
      <form onsubmit="handleChangePasswordSubmit(event)" class="space-y-3">
        <div>
          <label class="block text-xs font-semibold text-slate-700 mb-1">Mật khẩu hiện tại</label>
          <input type="password" id="chg-old-password" required placeholder="••••••••" class="w-full px-3 py-2 text-sm border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500">
        </div>
        <div>
          <label class="block text-xs font-semibold text-slate-700 mb-1">Mật khẩu mới (tối thiểu 8 ký tự)</label>
          <input type="password" id="chg-new-password" minlength="8" required placeholder="••••••••" class="w-full px-3 py-2 text-sm border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500">
        </div>
        <button type="submit" class="w-full py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-sm transition shadow-md shadow-indigo-200">
          Xác nhận đổi mật khẩu
        </button>
      </form>
    </div>
  </div>
  `);
})();
