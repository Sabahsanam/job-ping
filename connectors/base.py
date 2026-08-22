from abc import ABC, abstractmethod


class JobConnector(ABC):

    def __init__(self, company_name, careers_url):
        self.company_name = company_name
        self.careers_url = careers_url

    @abstractmethod
    def fetch_jobs(self):
        pass