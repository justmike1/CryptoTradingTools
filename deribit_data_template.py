import requests as rq
import json


class DeribitCALC:
    def __init__(self):
        self.deribit_url = "https://www.deribit.com/api/v2"
        self.pub_auth_endpoint = "/public/auth"
        self.private_endpoint = "/private/get_account_summary"  # Change endpoint to your liking docs.deribit.com/?shell
        self.currency = "BTC"
        self.client_id = ""
        self.client_secret = ""
        self.grant_type = "client_credentials"
        self.pub_params = {
            'client_id': self.client_id, 'client_secret': self.client_secret, 'grant_type': self.grant_type
        }
        self.public_auth = rq.get(url=self.deribit_url + self.pub_auth_endpoint, params=self.pub_params)
        self.data_auth = self.public_auth.json()
        self.pub_params['scope'] = str(self.data_auth['result']['scope']).split()[5]    # Scope has 8 values
        self.access_token = self.data_auth['result']['access_token']
        self.pri_params = {"currency": "BTC", "extended": "true"}
        self.private_data = rq.get(
            url=self.deribit_url + self.private_endpoint,
            headers={"Authorization": "Bearer " + self.access_token, "Content-Type": "application/json"},
            params=self.pri_params)
        self.data_private = self.private_data.json()

    def desired_data(self):
        print(json.dumps(self.data_private, sort_keys=True, indent=5))

    def testing(self):      # USE FOR TESTING SCOPE (ADD DeribitCALC().testing() to main)
        print(f"{self.pub_params}\n{self.access_token}")
        print(self.data_private["result"]["equity"])


if __name__ == '__main__':
    DeribitCALC().desired_data()
    # DeribitCALC().testing()       # USE FOR TESTING





