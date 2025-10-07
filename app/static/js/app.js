// 刪除確認
document.addEventListener('DOMContentLoaded', function() {
    // 刪除按鈕確認
    document.querySelectorAll('[data-confirm]').forEach(function(element) {
        element.addEventListener('click', function(e) {
            if (!confirm('確定要刪除嗎？此動作無法復原。')) {
                e.preventDefault();
                return false;
            }
        });
    });
});
