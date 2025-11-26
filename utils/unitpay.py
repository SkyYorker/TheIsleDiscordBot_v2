import hashlib
import os
import urllib.parse

PUBLIC_KEY = os.getenv('UNITPAY_PUBLIC_KEY')
PRIVATE_KEY = os.getenv('UNITPAY_PRIVATE_KEY')
PROJECT_ID = os.getenv('UNITPAY_PROJECT_ID')


class UnitPayUrlGenerator:
    @staticmethod
    def generate_signature(method: str, params: dict, secret_key: str) -> str:
        params_copy = params.copy()
        params_copy.pop('sign', None)
        params_copy.pop('signature', None)

        sorted_params = sorted(params_copy.items())

        string_components = []
        if method:
            string_components.append(method)

        for _, value in sorted_params:
            string_components.append(str(value))
        string_components.append(secret_key)

        string_to_hash = '{up}'.join(string_components)
        return hashlib.sha256(string_to_hash.encode('utf-8')).hexdigest()

    @staticmethod
    def generate_redirect_url(
            amount: float,
            account: str,
            description: str,
    ) -> str:
        params_for_signature = {
            'sum': amount,
            'account': account,
            'desc': description
        }

        signature = UnitPayUrlGenerator.generate_signature('', params_for_signature, PRIVATE_KEY)

        params_for_url = params_for_signature.copy()
        params_for_url['signature'] = signature

        base_url = f"https://unitpay.ru/pay/{PUBLIC_KEY}"

        query_string = urllib.parse.urlencode(params_for_url)

        return f"{base_url}?{query_string}"

