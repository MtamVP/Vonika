# 🚀 TỔNG QUAN EXTENSION: MARKET REPORT AUTOMATION

**Market Report Automation** là một module độc lập (extension) thuộc hệ sinh thái AI Vonika. Đây là hệ thống pipeline End-to-End tự động thu thập, phân tích và xuất bản các báo cáo thị trường tài chính chuyên sâu, sau đó đồng bộ trực tiếp với hệ thống RAG Backend.

---

## 🌟 1. Tính năng cốt lõi (Core Features)

- **Crawl Dữ Liệu Đa Nguồn Tự Động:** 
  Tự động quét và tải file PDF báo cáo chiến lược từ MASVN, Vietcap và tổng hợp tin tức nóng từ Vietstock.
- **Trích Xuất & Phân Tích bằng AI (Gemini):** 
  Sử dụng `pdfplumber` kết hợp với AI Prompt Engineering để bóc tách chính xác các bảng biểu phức tạp. AI sẽ phân tích số liệu thô và viết lại thành báo cáo tài chính chuẩn mực (với 5 phần phân tích chuyên sâu).
- **Tự Động Xuất Bản PDF Đẹp Mắt:** 
  Chuyển đổi văn bản Markdown của AI thành mã HTML và sử dụng `Playwright` (Chromium headless) để render ra file PDF chuyên nghiệp (tối ưu hóa font chữ, bảng biểu, ngắt dòng).
- **Lưu Trữ Thông Minh (Supabase Storage):** 
  Tự động upload file PDF vào Supabase Storage theo cấu trúc thư mục rõ ràng (`daily`, `weekly`, `monthly`, `quarterly`, `yearly`), đồng thời lưu metadata vào bảng `uploaded_files`.
- **Đồng Bộ RAG (Retrieval-Augmented Generation):** 
  Kích hoạt API Backend để nhúng (embed) dữ liệu từ file PDF vừa tạo vào vector database, giúp Vonika AI có thể truy vấn và trả lời câu hỏi của người dùng ngay lập tức.

---

## 🔄 2. Chiến lược "Data Rollup" (Cuộn dữ liệu tối ưu)

Để giải quyết bài toán rác dữ liệu khi số lượng báo cáo ngày quá lớn (250 file/năm), hệ thống được trang bị cơ chế **Data Rollup** (chạy ngầm qua Github Actions):

- **Tổng hợp định kỳ:** Tự động gộp nội dung các báo cáo ngày thành báo cáo Tuần, báo cáo Tuần thành Tháng/Quý/Năm.
- **Tối ưu chi phí lưu trữ:** Sau khi cuộn thành công, hệ thống tự động xóa sạch dữ liệu gốc (bao gồm xóa cả file vật lý trên Supabase Storage và dòng ghi nhận trong Database).

---

## 🎯 3. Tổng kết thành quả (Milestone)

- Hoàn thiện 100% Pipeline tự động mà không cần sự can thiệp của con người.
- Giải quyết triệt để vấn đề "vỡ định dạng" bảng biểu của Vietcap khi trích xuất PDF bằng cách tái tạo Markdown tables thông minh.
- CSS và Layout được tùy chỉnh thẩm mỹ cao cấp (Màu sắc `#003366`, căn chỉnh cột `38%/59%`, nhận diện highlight ticker...).
- Cơ chế linh hoạt: Dễ dàng cấu hình và thay thế các nguồn thu thập dữ liệu mới trong tương lai.
