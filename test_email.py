from email_service import send_verification_email


email = input("Enter email address to test: ").strip()

success, result = send_verification_email(email)

if success:
    print("Email sent successfully!")
    print("Verification token:", result)

else:
    print("Failed to send email.")
    print("Error:", result)