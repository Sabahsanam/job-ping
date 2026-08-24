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
from connectors.workable import WorkableConnector
from connectors.paycom import PaycomConnector
from connectors.jibe import JibeConnector
from connectors.talentbrew import TalentBrewConnector
from connectors.uber import UberConnector
from connectors.eightfold import EightfoldConnector
from connectors.successfactors import SuccessFactorsConnector
from connectors.oracle import OracleConnector


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
    # Electronic Arts
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
    # PAYCOM
    # --------------------------------------------

    if "paycomonline.net" in url:

        return PaycomConnector(
            company_name,
            careers_url
        )


    # --------------------------------------------
    # JIBE
    # GitHub + AMD currently use this platform
    # --------------------------------------------

    if (
        "github.careers" in url
        or "careers.amd.com" in url
    ):

        return JibeConnector(
            company_name,
            careers_url
        )


    # --------------------------------------------
    # SEGA
    # --------------------------------------------

    if "careers.sega.co.uk" in url:

        return SegaConnector(
            company_name,
            careers_url
        )


    # --------------------------------------------
    # WORKABLE
    # --------------------------------------------

    if "workable.com" in url:

        return WorkableConnector(
            company_name,
            careers_url
        )


    # --------------------------------------------
    # TALENTBREW / RADANCY
    # Intuit currently uses this platform
    # --------------------------------------------

    if "jobs.intuit.com" in url:

        return TalentBrewConnector(
            company_name,
            careers_url
        )


    # --------------------------------------------
    # UBER
    # --------------------------------------------

    if "jobs.uber.com" in url:

        return UberConnector(
            company_name,
            careers_url
        )


    # --------------------------------------------
    # ORACLE RECRUITING CANDIDATE EXPERIENCE
    # Oracle + TI + JPMorgan + American Express
    # --------------------------------------------

    if (
        "oraclecloud.com" in url
        and "/hcmui/candidateexperience/" in url
    ):

        return OracleConnector(
            company_name,
            careers_url
        )


    # --------------------------------------------
    # EIGHTFOLD
    # Microsoft + PayPal + Qualcomm
    # --------------------------------------------

    if (
        "jobs.careers.microsoft.com" in url
        or "apply.careers.microsoft.com" in url
        or "paypal.eightfold.ai" in url
        or "careers.qualcomm.com" in url
    ):

        # Microsoft's old careers URL redirects to
        # the current Eightfold careers site.
        if "jobs.careers.microsoft.com" in url:

            careers_url = (
                "https://apply.careers.microsoft.com/careers"
            )

        return EightfoldConnector(
            company_name,
            careers_url
        )


    # --------------------------------------------
    # SAP SUCCESSFACTORS / RMK
    # Paramount currently uses this platform
    # --------------------------------------------

    if "careers.paramount.com" in url:

        return SuccessFactorsConnector(
            company_name,
            careers_url
        )


    # --------------------------------------------
    # UNSUPPORTED
    # --------------------------------------------

    raise ValueError(
        f"Unsupported careers site: "
        f"{careers_url}"
    )