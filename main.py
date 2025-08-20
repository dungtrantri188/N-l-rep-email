import os
import imaplib
import email
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import google.generativeai as genai

# Lấy thông tin nhạy cảm từ biến môi trường của GitHub
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_APP_PASSWORD") # Dùng mật khẩu ứng dụng

# Cấu hình Gemini API
genai.configure(api_key=GEMINI_API_KEY)

# Hằng số máy chủ email
IMAP_SERVER = "imap.gmail.com"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

def get_email_body(msg):
    """Trích xuất nội dung text từ email."""
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            cdispo = str(part.get('Content-Disposition'))
            if ctype == 'text/plain' and 'attachment' not in cdispo:
                return part.get_payload(decode=True).decode('utf-8', errors='ignore')
    else:
        return msg.get_payload(decode=True).decode('utf-8', errors='ignore')

def send_reply(to_address, subject, body):
    """Gửi email trả lời."""
    msg = MIMEMultipart()
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = to_address
    msg['Subject'] = "Re: " + subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.sendmail(EMAIL_ADDRESS, to_address, msg.as_string())
        server.quit()
        print(f"Reply sent successfully to {to_address}")
    except Exception as e:
        print(f"Failed to send email: {e}")

def main():
    """Hàm chính để xử lý toàn bộ logic."""
    try:
        # Đọc cơ sở tri thức
        with open("knowledge_base.txt", "r", encoding="utf-8") as f:
            knowledge_base = f.read()
    except FileNotFoundError:
        print("Error: knowledge_base.txt not found!")
        return

    # Kết nối và đọc email
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        mail.select("inbox")
        
        status, messages = mail.search(None, "UNSEEN")
        if not messages[0]:
            print("No new emails.")
            mail.logout()
            return
        
        email_ids = messages[0].split()
        print(f"Found {len(email_ids)} new email(s).")

        for email_id in email_ids:
            _, msg_data = mail.fetch(email_id, "(RFC822)")
            msg = email.message_from_bytes(msg_data[0][1])

            from_address = email.utils.parseaddr(msg.get("From"))[1]
            subject = msg.get("Subject")
            body = get_email_body(msg)

            if not body:
                print(f"Could not extract body from email {email_id}. Skipping.")
                continue

            print(f"Processing email from: {from_address}")
            
            # Tạo prompt cho Gemini
            system_prompt = f"""
            Bạn là một trợ lý AI của Dũng. Nhiệm vụ của bạn là đọc email gửi đến Dũng và soạn một email trả lời THAY MẶT DŨNG.
            Hãy hành động như thể chính bạn là Dũng.

            --- ĐÂY LÀ THÔNG TIN VÀ PHONG CÁCH CỦA DŨNG ---
            {knowledge_base}
            --- KẾT THÚC THÔNG TIN ---

            QUY TẮC BẮT BUỘC:
            1. Trả lời dưới góc nhìn của Dũng (xưng "tôi").
            2. Giữ đúng giọng văn, phong cách đã được mô tả.
            3. Nếu câu hỏi nằm ngoài phạm vi kiến thức, hãy soạn câu trả lời lịch sự, nói rằng Dũng đã nhận được email và sẽ trả lời cá nhân sau. Ví dụ: "Cảm ơn bạn đã gửi email. Tôi đã nhận được tin và sẽ xem xét rồi phản hồi bạn sớm nhất có thể."
            4. Tuyệt đối không bịa đặt thông tin cá nhân về Dũng.

            Dưới đây là email cần trả lời:
            ---
            Người gửi: {from_address}
            Chủ đề: {subject}
            Nội dung:
            {body}
            ---

            Bây giờ, hãy soạn email trả lời hoàn chỉnh.
            """
            
            # Gọi Gemini API
            model = genai.GenerativeModel('gemini-1.5-pro-latest')
            response = model.generate_content(system_prompt)
            
            # Gửi email trả lời
            send_reply(from_address, subject, response.text)

        mail.logout()

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()