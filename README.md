# Cổng SEB — Django + HTML

Hệ thống cho nhiều giáo viên: đăng ký, đăng nhập, tạo kỳ thi riêng; học sinh mở file `.seb`, cổng tự xác minh BEK rồi mở Google Form nhúng.

## Cấu trúc

```text
gate/
├── backend/                 # Deploy lên Render
│   ├── config/              # Thiết lập Django, URL, ASGI
│   ├── exams/               # Tài khoản giáo viên, kỳ thi, xác minh, migrations/tests
│   ├── manage.py
│   ├── gate.py              # Entry point tương thích
│   ├── requirements.txt
│   ├── requirements.lock.txt
│   └── .env.example         # Mẫu biến môi trường, không tự nạp
├── frontend/                # Deploy lên Netlify
│   ├── index.html           # Cổng học sinh, liên kết tới trang giáo viên
│   ├── teacher.html         # Đăng ký, đăng nhập, quản lý kỳ thi
│   ├── netlify.toml         # Build, proxy đăng nhập và security headers
│   └── tests/               # Kiểm thử JavaScript, không đưa vào bản publish
├── render.yaml              # Blueprint với rootDir: backend
└── README.md
```

`.venv/` ở gốc chỉ là môi trường phát triển cục bộ, không đưa lên Git/deploy. SQLite và staticfiles cục bộ được giữ trong backend, đều được bỏ qua bởi Git. Production dùng PostgreSQL.

## Triển khai từ một Git repository (khuyến nghị)

Đưa toàn bộ mã nguồn lên repository của bạn. Render và Netlify có thể dùng cùng repository, nhưng chọn hai thư mục riêng. Không commit `.env`, `.venv`, database hoặc mật khẩu. Các tệp mới phải được commit/push thì dịch vụ mới thấy chúng.

### 1. Tạo frontend trên Netlify để lấy tên miền

Trong Netlify chọn **Add new project / Import an existing project**, kết nối repository và chọn nhánh muốn deploy.

- **Base directory:** `frontend`
- **Build command:** `mkdir -p public && cp index.html teacher.html public/`
- **Publish directory:** `public` (tính từ base directory; đường dẫn kết quả là `frontend/public`).
- Nếu có trường **Package directory**, để trống; base directory đã xác định thư mục dự án.

Netlify đọc `frontend/netlify.toml`. Build chỉ đưa hai file HTML vào public; proxy và headers được lấy từ cấu hình, không công khai backend hoặc các bài test.

Sau deploy, lấy URL ví dụ `https://truong-seb.netlify.app/`. Có thể đặt lại tên site để có tên miền dễ nhớ trước khi phát file SEB. Chưa có backend thì trang giáo viên sẽ hiển thị chờ; đây là bình thường ở bước này.

Không dùng cách kéo thả cả thư mục dự án lên Netlify. Upload chỉ HTML cũng chưa đủ vì đăng nhập cần proxy `/api/teacher/*` từ `netlify.toml`.

### 2. Tạo PostgreSQL trên Render

Trong Render chọn **New → Postgres**:

1. Đặt tên database, ví dụ `seb-gate-db`.
2. Chọn khu vực dự kiến dùng cho backend; web service và database nên cùng khu vực để dùng kết nối nội bộ.
3. Chọn gói phù hợp và tạo database.
4. Trong thông tin kết nối của database, sao chép **Internal Database URL**. Giữ riêng, không dán vào HTML hoặc commit vào repository.

Database lưu tài khoản giáo viên, mật khẩu đã băm, phiên đăng nhập, chủ sở hữu kỳ thi, BEK, link Google Form và lịch thi. Không cần tự tạo bảng; migrations sẽ chạy khi backend khởi động.

Render Postgres Free có thời hạn sử dụng (tài liệu hiện tại nêu 30 ngày). Đây không phải database miễn phí lưu trữ lâu dài. Chọn gói phù hợp và sao lưu dữ liệu nếu dùng cho kỳ thi thực tế.

### 3. Tạo backend Django trên Render

Chọn **New → Web Service**, kết nối cùng repository:

- **Name:** tên bạn chọn, ví dụ `gate-for-seb`.
- **Language / Runtime:** Python 3.
- **Root Directory:** `backend`.
- **Build Command:**

```sh
pip install -r requirements.txt && python manage.py collectstatic --noinput
```

- **Start Command:**

```sh
python manage.py migrate --noinput && uvicorn config.asgi:application --host 0.0.0.0 --port $PORT
```

- **Health Check Path:** `/api/health`.

Trong **Environment**, thêm các biến sau:

- `DJANGO_DEBUG` = `0`
- `DJANGO_SECRET_KEY` = chuỗi ngẫu nhiên dài do bạn tạo, giữ cố định giữa các lần deploy; không dùng giá trị ví dụ. Đổi khóa sẽ làm mất hiệu lực các phiên đã ký.
- `ALLOWED_HOSTS` = hostname thật của backend, ví dụ `gate-for-seb.onrender.com`; không có `https://` hay `/`.
- `FRONTEND_URL` = URL Netlify chính xác, ví dụ `https://truong-seb.netlify.app/`; phải có `https://`, dấu `/` cuối và không có query.
- `DATABASE_URL` = **Internal Database URL** ở bước 2.
- `PYTHON_VERSION` = `3.13.12` (đồng nhất cấu hình đã ghi trong Blueprint).

Có thể tự tạo SECRET_KEY bằng Python ở máy cá nhân, rồi dán kết quả trực tiếp vào Render:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

Bấm deploy. Lấy URL backend thật mà Render cấp. Nếu hostname khác tên bạn dự kiến, sửa `ALLOWED_HOSTS` và deploy lại. Truy cập `https://BACKEND-CUA-BAN/api/health`: khi sẵn sàng, kết quả là `{"status":"ready"}`. Trang gốc `/` của backend có thể trả 404 vì giao diện production đặt trên Netlify, không phải lỗi deploy.

Gói Free có thể ngủ khi không có traffic trong 15 phút; khởi động lại có thể mất khoảng một phút. Không dùng SQLite hoặc JSON trên ổ đĩa tạm của web service để lưu dữ liệu thi.

**Nếu cập nhật service Render cũ:** sửa Root Directory thành `backend`, thay build/start command như trên và kiểm tra đủ biến môi trường. Không giữ lệnh chạy FastAPI cũ.

### 4. Nối frontend với backend thật

Nếu backend vẫn là `https://gate-for-seb.onrender.com` thì không cần sửa hostname trong mã. Nếu Render cấp hostname khác, thay URL cũ tại:

1. `frontend/index.html`: hằng `API`.
2. `frontend/netlify.toml`: đích `to` của proxy `/api/teacher/*`.
3. `frontend/netlify.toml`: miền backend trong `Content-Security-Policy`, mục `connect-src`.

`teacher.html` gọi đường dẫn tương đối `/api/teacher/...`; **không đổi thành gọi thẳng Render**. Proxy giúp session cookie hoạt động cùng miền với trang giáo viên. Django kiểm tra CSRF theo `FRONTEND_URL`.

Commit/push thay đổi để Netlify deploy lại. Kiểm tra `FRONTEND_URL` trên Render đúng tên miền Netlify cuối cùng. Nếu đổi tên miền sau này, phải cập nhật cấu hình SEB, lưu file và lấy lại BEK.

### 5. Kiểm tra tài khoản và kỳ thi

1. Mở `https://TEN-TRANG.netlify.app/teacher.html` → **Tạo tài khoản**.
2. Đăng ký một tài khoản giáo viên; tài khoản mới chỉ quản lý kỳ thi của mình, không có quyền admin.
3. Tạo kỳ thi nháp với URL Google Form đầy đủ, kết thúc bằng `/viewform`; không dùng link `/edit` hoặc `forms.gle`.
4. Lấy Start URL → cấu hình SEB → lưu `.seb` → sao chép BEK → nhập vào kỳ thi → bật cho phép vào thi và lưu.
5. Đăng xuất/đăng nhập lại để xác nhận session hoạt động qua Netlify.
6. Mở file `.seb` bằng đúng phiên bản SEB đã duyệt để thử vào Form, điền và nộp bài.
7. Kiểm tra bài nộp ở Google Forms. Cổng không đọc được kết quả nộp trong iframe khác miền.

Nếu cần quản trị toàn hệ thống, chạy trong Render Shell:

```sh
python manage.py createsuperuser
```

Sau đó vào `https://BACKEND/admin/`. Giáo viên thông thường không cần tài khoản này để đăng ký. Nếu gói Render không có Shell, có thể chạy lệnh từ máy quản trị với biến môi trường production và External Database URL có TLS theo hướng dẫn nhà cung cấp. Không gửi chuỗi kết nối/mật khẩu cho người khác. Quên mật khẩu giáo viên hiện cần quản trị viên đặt lại; chưa tích hợp email khôi phục.

### Dùng Blueprint thay vì tạo web service thủ công

File `render.yaml` ở gốc repository đã có `rootDir: backend`. Có thể dùng **New → Blueprint** rồi chọn repository. Blueprint không tạo database; bạn vẫn cần cung cấp DATABASE_URL và FRONTEND_URL. Chọn cách này hoặc cách Web Service thủ công, không tạo hai service cho cùng mục đích. Kiểm tra lại ALLOWED_HOSTS theo hostname thực tế.

### Nếu muốn tách thành hai repository

- Repository backend chứa **nội dung bên trong** `backend/`; khi đó Render Root Directory để trống. Nếu dùng Blueprint, bỏ `rootDir: backend` sau khi đặt manifest vào repository backend.
- Repository frontend chứa **nội dung bên trong** `frontend/`; Netlify Base Directory để trống, build/publish giữ nguyên trong netlify.toml.
- Routes xem thử HTML của Django chỉ dùng khi DEBUG=1 và hai folder còn cạnh nhau; production không phụ thuộc folder frontend.

## Luồng sử dụng

**Giáo viên:** soạn Google Form → đăng ký/đăng nhập web → tạo nháp → lấy Start URL → cấu hình/lưu `.seb` → lấy BEK → bật kỳ thi → phát file.

**Học sinh:** cài bản SEB được duyệt → mở `.seb` → tự vào Start URL → chờ backend → xác minh → làm bài trên Google Form nhúng. Không cần tài khoản cổng; Google có thể yêu cầu đăng nhập theo thiết lập Form.

BEK lấy từ SEB sau khi lưu cấu hình cuối cùng, không dùng Config Key thay thế. Mỗi phiên bản/hệ điều hành được duyệt có thể cần BEK khác; nhập mỗi khóa một dòng. SEB phải hỗ trợ JavaScript API; hướng dẫn chính thức nêu Windows từ 3.3.2, nên thử bằng phiên bản chính thức hiện hành. Cấu hình URL filter phải cho phép cổng với query challenge, API backend và tài nguyên Google cần cho Form. Tự thử đăng nhập Google và nhúng Form trên máy học sinh trước khi thi.

## Heartbeat và giới hạn bảo vệ

- Trang hiển thị “Đang gọi backend, vui lòng chờ…” và tự thử lại khi backend chưa sẵn sàng.
- Sau xác minh, gọi heartbeat khoảng 4 phút/lần; lỗi mạng thử lại sau 15–20 giây. Không tải lại Form đang điền.
- Đóng trang hoặc chọn “Tôi đã nộp bài” sẽ dừng bộ gọi. Nút này không gửi bài thay nút Gửi của Google Forms.
- Máy ngủ, mạng mất, tab bị đình chỉ hoặc giới hạn nền tảng vẫn có thể làm heartbeat ngừng; không bảo đảm backend luôn thức.
- Lưu thay đổi kỳ thi thu hồi phiên cổng hiện tại. Đóng kỳ thi không tự ngăn Google Forms nhận bài đã mở; giáo viên quản lý việc nhận bài trong Google riêng.
- Cổng đối chiếu BEK qua API SEB, không trực tiếp kiểm tra chữ ký Authenticode của EXE. Không bảo đảm phát hiện mọi client bị sửa.
- Người biết URL Google Form có thể truy cập trực tiếp nếu quyền Google cho phép. Nhúng Form và challenge không loại bỏ giới hạn này.
- Challenge ngẫu nhiên có chữ ký, hiệu lực 10 phút, chưa phải loại dùng một lần. Proof bị đánh cắp có thể phát lại với đúng challenge trong thời hạn. Không chia sẻ BEK gốc.
- Tài khoản mới không được xác minh danh tính nghề nghiệp/email; dữ liệu được cách ly theo owner. Có thể bổ sung rate limit/kiểm duyệt đăng ký nếu vận hành công khai quy mô lớn.

## Chạy thử và kiểm thử cục bộ

Từ thư mục gốc dự án trên Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
$env:DJANGO_DEBUG='1'
$env:FRONTEND_URL='http://127.0.0.1:8000/'
.\.venv\Scripts\python.exe backend\manage.py migrate
.\.venv\Scripts\python.exe backend\manage.py runserver 127.0.0.1:8000
```

Trang giáo viên: `http://127.0.0.1:8000/teacher.html`. Chế độ DEBUG phục vụ hai HTML ở thư mục frontend để thử session cùng miền. Nếu thử luồng học sinh cục bộ, tạm đổi API trong bản HTML dùng thử sang `http://127.0.0.1:8000`; hoàn nguyên trước khi deploy. Trình duyệt thường bị từ chối xác minh là đúng.

```powershell
$env:DJANGO_DEBUG='1'
.\.venv\Scripts\python.exe backend\manage.py test exams
node frontend\tests\frontend.cjs
node frontend\tests\teacher.cjs
```

`requirements.lock.txt` ghi phiên bản đã kiểm thử. `.env.example` chỉ là mẫu; ứng dụng đọc biến môi trường, không tự đọc file .env.

## Xử lý lỗi thường gặp

- **400 / Invalid HTTP_HOST:** ALLOWED_HOSTS phải chứa hostname Render thực tế.
- **403 CSRF khi đăng ký:** FRONTEND_URL phải đúng origin Netlify, proxy phải được deploy; tải lại trang sau khi thay cấu hình để lấy token mới.
- **Trang giáo viên chờ mãi:** kiểm tra `/api/health` trên Render, đích proxy trong netlify.toml và biến DATABASE_URL.
- **Đăng nhập thành công nhưng không giữ phiên:** kiểm tra proxy/cookie qua cùng miền; không đổi teacher.html thành gọi trực tiếp cross-origin.
- **Không mở kỳ thi:** kiểm tra enabled, lịch thi, BEK và phiên bản SEB; Start URL phải đúng URL Netlify chuẩn, không chuyển qua miền khác.
- **Form không hiển thị:** kiểm tra Form hỗ trợ Embed HTML, quyền người trả lời, đăng nhập và cookie Google; cổng không tự mở cửa sổ khác để tránh mất heartbeat.

## Tài liệu chính thức

- Render Django: https://render.com/docs/deploy-django
- Render root directory: https://render.com/docs/monorepo-support
- Render PostgreSQL: https://render.com/docs/postgresql-creating-connecting
- Render Free: https://render.com/docs/free
- Netlify monorepo/base directory: https://docs.netlify.com/build/configure-builds/monorepos/
- Netlify proxy: https://docs.netlify.com/manage/routing/redirects/rewrites-proxies/
- SEB integration: https://www.safeexambrowser.org/developer/seb-integration.html
- SEB JavaScript API: https://safeexambrowser.org/developer/seb-config-key.html
- SEB Windows: https://safeexambrowser.org/windows/win_usermanual_en.html
- Google Forms: https://support.google.com/docs/answer/2839588?hl=en
