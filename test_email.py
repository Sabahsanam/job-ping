from emailer import send_job_alert

test_job = {
    "company": "Job Ping Test",
    "title": "Software Engineer I",
    "location": "Raleigh, NC",
    "url": "https://example.com/test-job"
}

send_job_alert(test_job)