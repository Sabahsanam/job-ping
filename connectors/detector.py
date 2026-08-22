from connectors.greenhouse import GreenhouseConnector
from connectors.lever import LeverConnector
from connectors.ashby import AshbyConnector
from connectors.smartrecruiters import SmartRecruitersConnector
from connectors.icims import ICIMSConnector
from connectors.workday import WorkdayConnector
from connectors.recruitee import RecruiteeConnector
from connectors.jobvite import JobviteConnector
from connectors.riot import RiotConnector
from connectors.avature import AvatureConnector
from connectors.valve import ValveConnector
from connectors.sega import SegaConnector


def get_connector(
    company_name,
    careers_url
):

    url = careers_url.lower()


    # --------------------------------------------
    # GREENHOUSE
    # --------------------------------------------

    if "greenhouse.io" in url:

        return GreenhouseConnector(
            company_name,
            careers_url
        )


    # --------------------------------------------
    # LEVER
    # --------------------------------------------

    if "lever.co" in url:

        return LeverConnector(
            company_name,
            careers_url
        )


    # --------------------------------------------
    # ASHBY
    # --------------------------------------------

    if "ashbyhq.com" in url:

        return AshbyConnector(
            company_name,
            careers_url
        )


    # --------------------------------------------
    # SMARTRECRUITERS
    # --------------------------------------------

    if "smartrecruiters.com" in url:

        return SmartRecruitersConnector(
            company_name,
            careers_url
        )


    # --------------------------------------------
    # ICIMS
    # --------------------------------------------

    if "icims.com" in url:

        return ICIMSConnector(
            company_name,
            careers_url
        )


    # --------------------------------------------
    # WORKDAY
    # --------------------------------------------

    if "myworkdayjobs.com" in url:

        return WorkdayConnector(
            company_name,
            careers_url
        )


    # --------------------------------------------
    # RECRUITEE
    # --------------------------------------------

    if "recruitee.com" in url:

        return RecruiteeConnector(
            company_name,
            careers_url
        )


    # --------------------------------------------
    # JOBVITE
    # --------------------------------------------

    if "jobvite.com" in url:

        return JobviteConnector(
            company_name,
            careers_url
        )


    # --------------------------------------------
    # RIOT GAMES
    # --------------------------------------------

    if "riotgames.com" in url:

        return RiotConnector(
            company_name,
            careers_url
        )


    # --------------------------------------------
    # AVATURE
    # Electronic Arts currently uses a branded
    # Avature careers domain.
    # --------------------------------------------

    if "jobs.ea.com" in url:

        return AvatureConnector(
            company_name,
            careers_url
        )


    # --------------------------------------------
    # VALVE
    # --------------------------------------------

    if "valvesoftware.com" in url:

        return ValveConnector(
            company_name,
            careers_url
        )


    # --------------------------------------------
    # UNSUPPORTED
    # --------------------------------------------
    if "careers.sega.co.uk" in url:

        return SegaConnector(
            company_name,
            careers_url
        )

    raise ValueError(
        f"Unsupported careers site: "
        f"{careers_url}"
    )