from emailer import send_job_digest


test_jobs = [
    {
        "id": "job-ping-email-test-001",
        "company": "Job Ping Test Company",
        "title": "Software Engineer I",
        "location": "Raleigh, NC",
        "url": "https://example.com/job-ping-test",
        "description": "This is a temporary Job Ping email test.",
        "source": "test"
    }
]


print("Sending Job Ping test email...")

email_sent = send_job_digest(test_jobs)

if email_sent:
    print("✅ TEST EMAIL SENT SUCCESSFULLY")
else:
    print("❌ TEST EMAIL FAILED")
    raise SystemExit(1)