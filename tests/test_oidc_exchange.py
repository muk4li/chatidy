"""Synthetic fixed HTTPS endpoints; no live provider or credentials."""
import io
import json
import unittest
from chatidy.oidc import OIDCSettings, OIDCError
from chatidy.oidc_exchange import (configured_settings, exchange_code,
                                   load_trusted_jwks)

class Reply:
    status = 200
    def __init__(self, payload):
        self.payload = io.BytesIO(payload)
    def __enter__(self):return self
    def __exit__(self,*args):self.payload.close()
    def read(self,size=-1):return self.payload.read(size)

class FakeTransport:
    def __init__(self, payload):
        self.payload=payload
        self.requests=[]
    def open(self, request, timeout=None):
        self.requests.append((request.full_url,request.get_method(),timeout))
        return Reply(self.payload)

class ExchangeTests(unittest.TestCase):
    def setUp(self):
        self.settings=OIDCSettings(
            "https://idp.example.invalid/application/o/app/",
            "https://idp.example.invalid/authorize",
            "https://idp.example.invalid/token",
            "https://idp.example.invalid/jwks",
            "synthetic-client",
            "https://chat.example.invalid/auth/callback")

    def test_fixed_endpoint_and_pkce_payload(self):
        transport=FakeTransport(json.dumps({"id_token":"synthetic-token"}).encode())
        token=exchange_code(self.settings,"synthetic-code","v"*48,
                            trusted_jwks=None,opener=transport)
        self.assertEqual(token,"synthetic-token")
        self.assertEqual(transport.requests,[("https://idp.example.invalid/token","POST",12)])

    def test_untrusted_endpoint_rejected_before_request(self):
        wrong=OIDCSettings(self.settings.issuer,
            self.settings.authorization_endpoint,"https://other.invalid/token",
            self.settings.jwks_uri,self.settings.client_id,self.settings.redirect_uri)
        transport=FakeTransport(b"{}")
        with self.assertRaises(OIDCError):
            exchange_code(wrong,"synthetic","v"*48,trusted_jwks=None,opener=transport)
        self.assertEqual(transport.requests,[])

    def test_invalid_response_and_missing_id_token(self):
        for data in (b"{}",b"not json",b"x"*65537,b"[]"):
            with self.subTest(data=data[:20]),self.assertRaises(OIDCError):
                exchange_code(self.settings,"synthetic","v"*48,
                              trusted_jwks=None,opener=FakeTransport(data))

    def test_jwks_loaded_from_fixed_url(self):
        transport=FakeTransport(b'{"keys":[{"kid":"synthetic"}]}')
        keys=load_trusted_jwks(self.settings,opener=transport)
        self.assertEqual(keys["keys"][0]["kid"],"synthetic")
        self.assertEqual(transport.requests,[("https://idp.example.invalid/jwks","GET",12)])

    def test_missing_configuration_rejected(self):
        with self.assertRaises(OIDCError):
            configured_settings({})
        config={
            "CHATIDY_OIDC_ISSUER":self.settings.issuer,
            "CHATIDY_OIDC_AUTHORIZE":self.settings.authorization_endpoint,
            "CHATIDY_OIDC_TOKEN":self.settings.token_endpoint,
            "CHATIDY_OIDC_JWKS":self.settings.jwks_uri,
            "CHATIDY_OIDC_CLIENT_ID":self.settings.client_id,
            "CHATIDY_PUBLIC_ORIGIN":"https://chat.example.invalid"
        }
        self.assertEqual(configured_settings(config),self.settings)

if __name__=="__main__":unittest.main()
