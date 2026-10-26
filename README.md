# Cổng SEB — Neon Free + Render Free + Netlify

Frontend HTML trên Netlify. Backend Django trên Render. Tài khoản giáo viên và kỳ thi lưu riêng trên **Neon PostgreSQL**, không mất khi backend Render restart/deploy.

## Chỉ cần nhập hai giá trị trên Render

- **FRONTEND_URL:** địa chỉ website Netlify.
- **DATABASE_URL:** chuỗi kết nối lấy từ Neon.

Blueprint tự tạo khóa bí mật, chọn Python, chạy migrations và nhận tên miền backend. Không cần tự tạo database trên Render, cấu hình ổ đĩa hay nhập ALLOWED_HOSTS. Đăng nhập và quyền sở hữu kỳ thi giữ nguyên.

## Bước 1 — Netlify

Kết nối repository `binanddev/Gate_Seb`, chọn nhánh **MinhTien**:

- Base directory: `frontend`
- Build command: `mkdir -p public && cp index.html teacher.html public/`
- Publish directory: `public`

Các thiết lập build/proxy có trong `frontend/netlify.toml`. Deploy để nhận URL, ví dụ `https://truong-seb.netlify.app/`. Trang có thể hiện chờ khi backend chưa được thiết lập.

## Bước 2 — Neon Free

1. Vào https://neon.com và tạo tài khoản/gói **Free**.
2. Tạo project, ví dụ `seb-gate`. Chọn khu vực gần Singapore nếu có, vì backend được cấu hình ở Singapore.
3. Mở **Connect**, chọn database mặc định và bật **Connection pooling** nếu có lựa chọn này.
4. Sao chép **connection string** dạng `postgresql://...`. Chỉ lấy URL, không lấy cả lệnh `psql` hoặc dấu nháy bọc ngoài. Giữ các tham số như `sslmode=require` và `channel_binding=require` nếu Neon cung cấp.
5. Dán riêng chuỗi này vào DATABASE_URL trên Render ở bước tiếp theo. Không đặt chuỗi kết nối trong HTML hoặc đẩy lên Git.

Không cần tạo bảng thủ công. Backend tạo bảng khi khởi động. Dùng cùng một database/branch Neon cho các lần deploy tiếp theo để giữ dữ liệu.

## Bước 3 — Render Blueprint

1. Vào Render → **New → Blueprint**.
2. Chọn repository **Gate_Seb**, nhánh **MinhTien**, file `render.yaml` ở gốc.
3. Nhập đúng hai trường:
   - FRONTEND_URL: dán URL Netlify từ bước 1. Có thể dán chỉ tên miền; ứng dụng tự thêm HTTPS và dấu `/` cuối.
   - DATABASE_URL: dán chuỗi kết nối Neon từ bước 2.
4. Chọn **Deploy Blueprint**. Blueprint chỉ tạo một web service Free, không tạo Render PostgreSQL hoặc disk trả phí.
5. Khi deploy xong, mở `https://TEN-BACKEND.onrender.com/api/health`. Khi backend và Neon kết nối được, trả về `{"status":"ready"}`.

Render dùng `/api/live` để kiểm tra tiến trình mà không đánh thức Neon liên tục. Trang học sinh vẫn dùng `/api/health` để kiểm tra kết nối database trước khi vào thi.

### Nếu đã có web service Render

Không cần tạo thêm service. Cập nhật repository/nhánh, Root Directory `backend`, rồi đặt:

Build command:
```sh
pip install -r requirements.txt && python manage.py collectstatic --noinput
```

Start command:
```sh
python manage.py migrate --noinput && uvicorn config.asgi:application --host 0.0.0.0 --port $PORT
```

Health Check Path: `/api/live`.

Giữ nguyên DJANGO_SECRET_KEY hiện có, cập nhật FRONTEND_URL và DATABASE_URL sang Neon, rồi deploy. Nếu chưa có khóa bí mật vì không tạo bằng Blueprint, dùng chức năng Generate của Render để tạo một lần. Không cần thêm ALLOWED_HOSTS cho hostname Render mặc định; tên miền riêng có thể khai báo qua biến này.

**Database mới không tự có dữ liệu cũ.** Nếu đã có tài khoản/kỳ thi trên SQLite hoặc database khác, cần chuyển dữ liệu riêng; đừng xóa database cũ trước khi kiểm tra bản chuyển. Mã này không tự di chuyển hay xóa dữ liệu.

## Bước 4 — Nối frontend tới backend

Nếu Render cấp đúng `https://gate-for-seb.onrender.com` thì bỏ qua bước sửa URL. Nếu khác, thay URL cũ tại ba vị trí:

1. `frontend/index.html`: hằng `API`.
2. `frontend/netlify.toml`: đích `to` của proxy `/api/teacher/*`.
3. `frontend/netlify.toml`: miền backend trong `connect-src`.

Commit/push để Netlify deploy lại. Không đổi teacher.html sang gọi trực tiếp Render: trang này dùng proxy cùng miền để đăng nhập ổn định. FRONTEND_URL trên Render phải khớp tên miền Netlify thực tế.

## Bước 5 — Dùng thử

1. Vào `/teacher.html` trên Netlify → đăng ký tài khoản.
2. Soạn đề trên Google Forms, lấy URL đầy đủ `/viewform` (không dùng `/edit` hoặc forms.gle).
3. Tạo kỳ thi nháp trên cổng → lấy Start URL.
4. Dán Start URL vào SEB Config Tool → hoàn tất cấu hình → lưu `.seb` → lấy **Browser Exam Key**.
5. Dán BEK vào kỳ thi → bật cho phép vào thi → lưu → gửi file `.seb` cho học sinh.
6. Học sinh mở file → cổng tự gọi backend → xác minh → chuyển trực tiếp sang Form. Không cần tài khoản cổng; Google có thể yêu cầu đăng nhập theo thiết lập Form.

Mỗi giáo viên chỉ quản lý kỳ thi của mình. Không dùng Config Key thay BEK. Nếu đổi cấu hình SEB, lưu lại và cập nhật BEK. Cho phép URL Google Form và các trang đăng nhập Google cần thiết trong URL filter của SEB; thử chuyển trang và nộp bài bằng SEB thật trước khi thi.

## Điều cần biết về gói miễn phí

Neon Free có giới hạn lưu trữ/tài nguyên. Compute có thể ngủ rồi tự thức khi có truy vấn, nhưng dữ liệu lưu độc lập với Render. Render Free cũng có thể ngủ; giao diện đã có trạng thái chờ và thử lại. Không có cam kết phục vụ số lượng học sinh bất kỳ: cần thử tải và theo dõi quota Neon.

Cổng chỉ xác minh rồi chuyển ngay tới đúng URL Google Form đã lưu bằng điều hướng trang hiện tại. Không dùng iframe, không cần bấm nút mở bài, không thêm embedded=true và giữ nguyên các tham số URL của giáo viên. Khi chuyển đi, mã JavaScript của cổng dừng; không còn heartbeat trong lúc làm bài. Backend có thể ngủ trở lại mà không ảnh hưởng Form đã mở trên Google.

Cổng vẫn hiển thị chờ và tự thử lại nếu chưa kết nối được backend. Xác minh sai không chuyển trang. Cổng kiểm tra BEK, không trực tiếp kiểm tra EXE và không ngăn truy cập Form bằng URL trực tiếp. Học sinh nộp bài bằng nút Gửi của Google Forms. API heartbeat cũ còn giữ để tương thích, nhưng frontend mới không gọi nữa.

## Thư mục và chạy cục bộ

- `backend/`: Django, API, migrations, kiểm thử backend; SQLite chỉ dùng phát triển cục bộ.
- `frontend/`: hai HTML, cấu hình Netlify, kiểm thử JavaScript.
- `render.yaml`: cấu hình backend Render Free với hai trường nhập.
- `backend/.env.example`: mẫu tham khảo; không tự nạp .env.

Từ thư mục gốc, PowerShell:
```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
$env:DJANGO_DEBUG='1'
$env:FRONTEND_URL='http://127.0.0.1:8000/'
.\.venv\Scripts\python.exe backend\manage.py migrate
.\.venv\Scripts\python.exe backend\manage.py runserver 127.0.0.1:8000
```

Để thử SQLite cục bộ, không đặt DATABASE_URL. Trang giáo viên thử tại `http://127.0.0.1:8000/teacher.html`. Nếu thử luồng học sinh cục bộ, đổi API trong bản HTML dùng thử sang localhost rồi hoàn nguyên trước khi push.

Kiểm thử:
```powershell
$env:DJANGO_DEBUG='1'
.\.venv\Scripts\python.exe backend\manage.py test exams
node frontend\tests\frontend.cjs
node frontend\tests\teacher.cjs
```

Quản trị hệ thống tùy chọn: chạy `python manage.py createsuperuser` trong môi trường backend có kết nối Neon rồi vào `/admin/`. Giáo viên tự đăng ký, không cần bước này. Chưa tích hợp email khôi phục mật khẩu; quản trị viên có thể đặt lại trong admin.

## Tài liệu chính thức

- Neon và Django: https://neon.com/blog/python-django-and-neons-serverless-postgres
- Neon Free/quota hiện hành: https://neon.com/pricing
- Render Blueprint: https://render.com/docs/blueprint-spec
- Netlify proxy: https://docs.netlify.com/manage/routing/redirects/rewrites-proxies/
- SEB JavaScript API: https://safeexambrowser.org/developer/seb-config-key.html
