# KẾ HOẠCH PHÁT TRIỂN HỆ THỐNG BÁO CÁO THỊ TRƯỜNG TỰ ĐỘNG (MARKET REPORT)

Bản kế hoạch này lưu trữ các chiến lược cốt lõi và kiến trúc của hệ thống tự động sinh báo cáo tài chính hằng ngày bằng AI Vonika.

---

## 1. Mục tiêu hệ thống
- Tự động tải báo cáo từ nguồn (MASVN, Vietstock).
- Trích xuất dữ liệu, tổng hợp tin tức và số liệu giao dịch ròng.
- Dùng AI (Gemini 2.5 Flash) để phân tích, nhận định và tự động viết báo cáo chuyên sâu.
- Tạo báo cáo file PDF (bằng Playwright) với giao diện biểu đồ chuyên nghiệp.

## 2. Kiến trúc 5 phần của Báo Cáo
Báo cáo luôn tuân thủ chuẩn mực chuyên gia tài chính cấp cao, gồm đúng 5 phần:
- **PHẦN 1: TỔNG QUAN & BẢNG SỐ LIỆU THỊ TRƯỜNG** (Bảng biến động chỉ số, định giá khu vực).
- **PHẦN 2: BỨC TRANH TOÀN CẢNH & CỘI NGUỒN DÒNG TIỀN** (Nhận định nguyên nhân chi phối dòng tiền).
- **PHẦN 3: ĐỘNG LỰC NHÓM NGÀNH & ĐIỂM SÁNG DOANH NGHIỆP** (Phân tích ngành nổi bật, mua bán ròng khối ngoại/tự doanh).
- **PHẦN 4: ĐỊNH VỊ RỦI RO & KHUNG CHIẾN LƯỢC QUẢN TRỊ** (Kịch bản cơ sở 70% và rủi ro 30%, tư vấn phân bổ vốn).
- **PHẦN 5: TÓM GỌN TIN TỨC VÀ TÁC ĐỘNG NGOẠI BIÊN** (Tin vĩ mô, doanh nghiệp và đánh giá cơ hội/rủi ro).

---

## 3. Chiến lược "Data Rollup" (Cuộn dữ liệu) - TINH HOA HỆ THỐNG
Trong ngành Data Engineering, chiến lược này gọi là **Data Rollup**. Đây là giải pháp hoàn hảo để lưu trữ dài hạn báo cáo PDF mà không làm nghẽn hệ thống.

### Nguyên lý hoạt động (Chu kỳ cuộn):
Thay vì phải gánh ~260 file báo cáo ngày (chiếm khoảng 500MB+ mỗi năm), hệ thống sẽ chủ động "cuộn" và tổng hợp lại theo trình tự thời gian:

- **Báo cáo Ngày:** Được cào và tạo ra từ Thứ 2 đến Thứ 6 hằng tuần.
- **Báo cáo Tuần:** Vào cuối tuần (Thứ 7, CN), hệ thống không cào dữ liệu mới mà sẽ lấy tất cả file PDF của các ngày trong tuần đó để tóm tắt thành 1 "Báo cáo Tuần". Sau khi có báo cáo tuần, các **báo cáo ngày của tuần đó sẽ bị xóa sạch**.
- **Báo cáo Tháng:** Cuối tháng, hệ thống gom các "Báo cáo Tuần" lại tóm tắt thành "Báo cáo Tháng". Sau khi xong, các **báo cáo tuần của tháng đó sẽ bị xóa sạch**.
- **Báo cáo Quý (3 tháng):** Cuối mỗi quý, gom 3 Báo cáo Tháng lại thành "Báo cáo Quý". (Lưu ý: Từ cấp độ Báo cáo Tháng, Quý, Nửa năm, Năm trở đi, **KHÔNG ĐƯỢC XÓA** bất kỳ file nào).
- **Báo cáo Nửa năm (6 tháng):** Gom 2 Báo cáo Quý lại.
- **Báo cáo Năm:** Tổng hợp 4 Báo cáo Quý lại thành báo cáo toàn cảnh của năm.

Nhờ chu trình "cuộn" tầng tầng lớp lớp này, tổng số file lưu trữ cứng trên Supabase cho một năm chỉ còn lại tầm 12 Báo cáo Tháng + 4 Báo cáo Quý + 2 Báo cáo Nửa năm + 1 Báo cáo Năm (khoảng chưa tới 20 file).

### 2 Lợi ích khổng lồ:
1. **Tiết kiệm dung lượng cực mạnh:** Với giới hạn lưu trữ đám mây (như Supabase 1GB), cách làm này biến bộ nhớ trở nên vô tận vì không bị rác báo cáo ngày chất đống.
2. **Tối ưu sức mạnh cho RAG (AI Vonika):** 
   - 1 năm sau, nếu hỏi AI: *"Thị trường Quý 1 năm ngoái biến động ra sao?"*
   - Thay vì AI phải lục tung và nhồi nhét 60 file báo cáo ngày (gây lỗi Context Overflow - ngộp token, dẫn đến sập hoặc trả lời sai ngớ ngẩn).
   - AI Vonika chỉ cần bốc duy nhất **1 file "Báo cáo Quý 1"** (đã được tinh lọc) ra đọc. Câu trả lời sẽ cực nhanh, cực chuẩn xác và tốn cực ít Token.

---

## 4. Bảo trì và Tự động hóa
- Quá trình chạy nằm hoàn toàn trên **GitHub Actions** (Workflow `market_report.yml`).
- Mọi print log thừa trong Python đã được xóa sạch để log Github Actions luôn gọn gàng.
- Cơ chế Auto-Retry tự động bọc lỗi API (Gemini 503) được kích hoạt để đảm bảo job luôn thành công mà không bị crash giữa chừng vì nghẽn mạng.

---

## 5. Chiến thuật "Canh me" (Polling Strategy) & Chạy an toàn (Idempotency)
Vì giờ giấc có báo cáo từ các trang web (MASVN, Vietstock) thường trễ và "hên xui", hệ thống áp dụng chiến thuật canh me thông minh để không bỏ sót báo cáo nhưng cũng không chạy thừa:

- **Khung giờ chạy (Cron):** Đặt lịch chỉ chạy từ Thứ 2 đến Thứ 6 (hoàn toàn bỏ qua T7, CN).
- **Chiến thuật nhiều khung giờ:** GitHub Actions sẽ được cài đặt chạy quét vào 3 khung giờ liên tiếp (Ví dụ: 19:30, 20:30, 21:30).
- **Cơ chế Tự thoát (Idempotency) dựa trên Tên File:** 
  - File PDF sinh ra luôn có tên định dạng chứa ngày của báo cáo, ví dụ: `Báo cáo thị trường ngày 19-08-2026.pdf`.
  - Mỗi khi Github Actions thức dậy (vd: 19h30), dòng lệnh đầu tiên nó sẽ kiểm tra trên kho lưu trữ: **"Đã có file báo cáo mang ngày hôm nay chưa?"**.
  - Nếu **CHƯA CÓ** (hoặc file báo cáo gần nhất là của ngày hôm qua/trước đó) -> Hệ thống hiểu là bài mới hôm nay chưa lên -> Nó sẽ chạy script để cào và tạo file. (Nếu web vẫn chưa có bài mới, nó sẽ tự tắt và đợi khung giờ sau).
  - Nếu **ĐÃ CÓ FILE MANG NGÀY HÔM NAY** (ví dụ do lúc 14h bạn bấm nút thủ công tạo ra, hoặc do khung giờ trước cào thành công) -> Hệ thống tự động nhận diện là đã xong việc -> Thoát ngay lập tức (bỏ qua luôn) mà không làm gì thêm, tiết kiệm tài nguyên tuyệt đối.

---

## 6. Trải nghiệm người dùng (UX/UI) trên Vonika
- Trên giao diện của Vonika, người dùng sẽ có một nút bấm để theo dõi hoặc gọi lệnh tạo báo cáo.
- **Thanh Progress Bar:** Giao diện bắt buộc phải có thanh trạng thái tiến trình (progress bar) hiển thị % hoặc dòng chữ báo hiệu quá trình cào dữ liệu, xử lý AI và xuất PDF để tăng trải nghiệm người dùng, tránh việc người dùng tưởng hệ thống bị treo.
- **Không Ghi Đè Lịch Sử (No Overwrite):** Nguyên tắc tuyệt đối trên UI là không bao giờ làm mất hay ghi đè lên các báo cáo cũ của các ngày/tuần/tháng/quý trước đó (tôn trọng triệt để chiến lược Data Rollup). Trong cùng một ngày, nếu bấm tạo lại thì hệ thống chỉ ghi đè lên chính file của ngày hôm đó (chỉ giữ 1 bản mới nhất cho 1 ngày).

---

## 7. Rủi ro Vận hành & Phòng ngừa
Đây là các cảnh báo quan trọng (Enterprise-level Warning) cần lưu ý khi vận hành:
- **Xung đột ghi đè (Conflict) trên Supabase:** Chú ý dùng cờ `upsert: true` trong API của Supabase khi upload file để tránh lỗi văng conflict nếu file PDF ngày hôm đó đã tồn tại.
