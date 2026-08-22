import os
import random
from html import escape

import resend
from dotenv import load_dotenv


load_dotenv()


# ------------------------------------------------
# JOB PING QUOTES
# ------------------------------------------------

JOB_PING_QUOTES = [
    "Think about the money!! 💸",
    "Jet ski. Apartment. Plane tickets. Lock in. 🫡",
    "We need to travel. Please get employed. ✈️",
    "Your future apartment would like a word. 🏙️",
    "One application closer to being annoyingly successful.",
    "Corporate baddie loading… 💼✨",
    "Imagine checking LinkedIn from Italy. Exactly.",
    "The job market tried it. Anyway, keep going.",
    "A salary would look really cute on you.",
    "Future you said to apply.",
    "December graduation is coming. Let us MOVE.",
    "For the concerts. For the trips. For the little treats.",
    "Job Ping said GET UP 📢",
    "Unfortunately, our expensive taste requires employment.",
    "Money cannot buy happiness. It can, however, buy plane tickets.",
    "The lore demands a successful career arc.",
    "New era needs new income.",
    "Plot development: you get the offer.",
    "Do it for the post-grad apartment.",
    "Be delusional. Be qualified. Apply anyway. 🎀",
    "Today's agenda: become employed and fabulous.",
    "Another day, another opportunity to secure the bag.",
    "Your future boarding pass is counting on you. ✈️",
    "Consider this your tiny career fairy notification. 🧚‍♀️",
    "Cute job alert just dropped.",
    "Applications first. Little treat afterward.",
    "The résumé is résumé-ing.",
    "May your applications be strong and your recruiters responsive.",
    "There is a paycheck somewhere with your name on it.",
    "We're building the plot one application at a time."
]


def get_random_quote():
    return random.choice(
        JOB_PING_QUOTES
    )


# ------------------------------------------------
# FORMAT LOCATION
# ------------------------------------------------

def format_location(location):
    if not location:
        return "Location not listed"

    return escape(
        str(location)
    )


# ------------------------------------------------
# BUILD ONE JOB CARD
# ------------------------------------------------

def build_job_card(job):

    company = escape(
        str(
            job.get(
                "company",
                "Unknown Company"
            )
        )
    )

    title = escape(
        str(
            job.get(
                "title",
                "Untitled Role"
            )
        )
    )

    location = format_location(
        job.get("location")
    )

    url = escape(
        str(
            job.get(
                "url",
                "#"
            )
        )
    )

    return f"""
    <div style="
        background: #ffffff;
        border: 1px solid #f0dfe8;
        border-radius: 18px;
        padding: 22px;
        margin-bottom: 16px;
        box-shadow: 0 4px 14px rgba(90, 50, 70, 0.06);
    ">

        <div style="
            font-size: 13px;
            font-weight: 700;
            color: #c56f98;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 8px;
        ">
            {company}
        </div>

        <div style="
            font-size: 20px;
            line-height: 1.35;
            font-weight: 700;
            color: #352b31;
            margin-bottom: 8px;
        ">
            {title}
        </div>

        <div style="
            font-size: 14px;
            color: #75666e;
            margin-bottom: 18px;
        ">
            📍 {location}
        </div>

        <a
            href="{url}"
            style="
                display: inline-block;
                background: #df8fb3;
                color: #ffffff;
                text-decoration: none;
                font-size: 14px;
                font-weight: 700;
                padding: 11px 18px;
                border-radius: 999px;
            "
        >
            View Job →
        </a>

    </div>
    """


# ------------------------------------------------
# BUILD EMAIL
# ------------------------------------------------

def build_digest_html(jobs):

    quote = get_random_quote()

    escaped_quote = escape(
        quote
    )

    job_count = len(
        jobs
    )

    job_word = (
        "job"
        if job_count == 1
        else "jobs"
    )

    cards = "".join(
        build_job_card(job)
        for job in jobs
    )

    return f"""
    <!DOCTYPE html>

    <html>

    <body style="
        margin: 0;
        padding: 0;
        background: #fff7fb;
        font-family:
            -apple-system,
            BlinkMacSystemFont,
            'Segoe UI',
            Arial,
            sans-serif;
        color: #352b31;
    ">

        <div style="
            width: 100%;
            padding: 35px 15px;
            box-sizing: border-box;
        ">

            <div style="
                max-width: 650px;
                margin: 0 auto;
            ">

                <!-- HEADER -->

                <div style="
                    background:
                        linear-gradient(
                            135deg,
                            #f8c8dc,
                            #f6dbe7
                        );
                    border-radius: 24px;
                    padding: 36px 28px;
                    text-align: center;
                    margin-bottom: 24px;
                ">

                    <div style="
                        font-size: 34px;
                        margin-bottom: 6px;
                    ">
                        💌
                    </div>

                    <div style="
                        font-size: 29px;
                        font-weight: 800;
                        color: #6d4056;
                        margin-bottom: 12px;
                    ">
                        JOB PING!
                    </div>

                    <div style="
                        font-size: 16px;
                        line-height: 1.5;
                        color: #805d6e;
                    ">
                        {job_count} new {job_word}
                        just entered the group chat ✨
                    </div>

                </div>


                <!-- RANDOM QUOTE -->

                <div style="
                    background: #fff0f6;
                    border: 1px solid #f1cadc;
                    border-radius: 18px;
                    padding: 20px 24px;
                    text-align: center;
                    margin-bottom: 26px;
                ">

                    <div style="
                        font-size: 12px;
                        font-weight: 700;
                        text-transform: uppercase;
                        letter-spacing: 1.5px;
                        color: #c56f98;
                        margin-bottom: 8px;
                    ">
                        today's job ping energy
                    </div>

                    <div style="
                        font-size: 18px;
                        line-height: 1.5;
                        font-weight: 600;
                        color: #5d3e4d;
                    ">
                        “{escaped_quote}”
                    </div>

                </div>


                <!-- JOB CARDS -->

                {cards}


                <!-- FOOTER -->

                <div style="
                    text-align: center;
                    padding: 25px 10px 10px 10px;
                    color: #a48896;
                    font-size: 13px;
                    line-height: 1.6;
                ">

                    <div style="
                        font-weight: 700;
                        color: #c56f98;
                        margin-bottom: 4px;
                    ">
                        Job Ping 💗
                    </div>

                    Finding the opportunities
                    so you do not have to refresh
                    47 career pages yourself.

                    <br><br>

                    go get that offer ♡

                </div>

            </div>

        </div>

    </body>

    </html>
    """


# ------------------------------------------------
# SEND DIGEST
# ------------------------------------------------

def send_job_digest(jobs):

    if not jobs:
        return False

    api_key = os.getenv(
        "RESEND_API_KEY"
    )

    recipients_text = os.getenv(
        "ALERT_RECIPIENTS",
        ""
    )

    recipients = [
        email.strip()
        for email in recipients_text.split(",")
        if email.strip()
    ]


    if not api_key:
        print(
            "RESEND_API_KEY is missing."
        )

        return False


    if not recipients:
        print(
            "ALERT_RECIPIENTS is missing."
        )

        return False


    resend.api_key = api_key


    job_count = len(
        jobs
    )

    subject = (
        f"💌 Job Ping! "
        f"{job_count} new "
        f"{'job' if job_count == 1 else 'jobs'} ✨"
    )


    html = build_digest_html(
        jobs
    )


    try:

        resend.Emails.send({
            "from": (
                "Job Ping "
                "<onboarding@resend.dev>"
            ),
            "to": recipients,
            "subject": subject,
            "html": html
        })


        print(
            "Job Ping digest sent successfully! 💌"
        )

        return True


    except Exception as error:

        print(
            f"Could not send Job Ping digest: "
            f"{error}"
        )

        return False