"""
Welcome to the trial 

Add some small solutions to the code or/and add some comments where you think improvements can be made.

This test should take you no more than 30 minutes.

Using AI is not allowed.
"""

import random
import time
from enum import Enum
from logging import getLogger  # The method ```getLogger(__name__)``` is better because it looks for any existing logger configurations for the given name while the ```Logger(__name__)``` is creating a default logger with the name and sets the default log level to 0.

import requests
from prefect import Task, flow
from prefect.server.schemas.states import StateType
from requests import RequestException

from schemas import HodlHodlOfferBase, HodlHodlUserBase, settings


class Scraper_Names(Enum):
    hodlhodl = "hodlhodl"


class Scraper:
    def __init__(self, **kwargs):
        self.proxy = kwargs.get("proxy", None)
        self.logger = getLogger(__name__)  # Reflect the change as in the imports
        self.requester = requests
        self.total_offer_percent_to_scrape = kwargs.get("total_offer_percent_to_scrape", 100)

    def get_currency_list(self):
        url = 'https://hodlhodl.com/api/frontend/currencies'
        currency_list = []
        try:
            currencies = self.requester.get(url).json()
            for curr in currencies['currencies']:
                currency_list.append(curr.get("code"))
        except RequestException as e:
            self.logger.error("Error fetching currency list: %s", e)

        return currency_list

    def get_and_post_offers(self, curr, trading_type):
        url = f"https://hodlhodl.com/api/frontend/offers?filters[currency_code]={curr}&pagination[offset]=0&filters[side]={trading_type}&facets[show_empty_rest]=true&facets[only]=false&pagination[limit]=100"
        try:
            resp = self.requester.get(url).json()
            for offer in resp.get("offers"):
                offer_info = self.create_offer_data(offer)
                seller_info = self.create_seller_data(offer)
                self.post_data_to_api(seller_info, offer_info)
        except RequestException as e:
            self.logger.error("Error fetching offers: %s", e)

    def create_offer_data(self, offer):
        return HodlHodlOfferBase(
            offer_identifier=offer.get("id"),
            fiat_currency=offer.get("asset_code"),
            country_code=offer.get("country_code"),
            trading_type_name=offer.get("side"),
            trading_type_slug=offer.get("side"),
            payment_method_name=offer.get("payment_methods")[0].get("type") if offer.get("payment_methods") else None,
            payment_method_slug=offer.get("payment_methods")[0].get("type") if offer.get("payment_methods") else None,
            description=offer.get("description"),
            currency_code=offer.get("currency_code"),
            coin_currency=offer.get("currency_code"),
            price=offer.get("price"),
            min_trade_size=offer.get("min_amount"),
            max_trade_size=offer.get("max_amount"),
            site_name='hodlhodl',
            margin_percentage=0,
            headline=''
        )

    def create_seller_data(self, offer):
        return HodlHodlUserBase(
            username=offer.get("trader").get("login"),
            feedback_score=offer.get("trader").get("rating") if offer.get("trader").get("rating") else 0,
            completed_trades=offer.get("trader").get("trades_count"),
            seller_url=offer.get("trader").get("url"),
            profile_image='',
            trade_volume=0
        )

    def post_data_to_api(self, seller_info, offer_info):
        data = {
            "user": seller_info.dict(),
            "offer": offer_info.dict(),
        }

        cc = offer_info.dict()["country_code"]
        if cc == "Global":
            cc = 'GL'

        params = {
            "country_code": cc,
            "payment_method": offer_info.dict()["payment_method_name"],
            "payment_method_slug": offer_info.dict()["payment_method_slug"],
        }

        try:
            return print(params, data)

        except RequestException as e:
            self.logger.error("Error posting data to API: %s", e)

    def starter(self):
        currencies_list = self.get_currency_list()
        for curr in currencies_list:
            for trading_type in ["buy", "sell"]:
                rate = Task(self.get_and_post_offers,
                            name=f"get hodlhodl offers"
                            ).submit(curr, trading_type, return_state=True)
                if rate.type != StateType.COMPLETED or not rate.result():
                    self.logger.error('Task failed')
                    continue
                self.logger.debug("Got %s rates", rate)

                return rate.result()


@flow
def get_hodlhodl_offers():
    return Scraper().starter()


if __name__ == "__main__":
    get_hodlhodl_offers()
