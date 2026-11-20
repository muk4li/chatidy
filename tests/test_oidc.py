"""AUTH-007: synthetic RS256 OIDC verification and PKCE; no real secrets."""
import base64
import json
import time
import unittest
from urllib.parse import parse_qs, urlsplit

try:
    import jwt
    from cryptography.hazmat.primitives.asymmetric import rsa
    from chatidy.oidc import (OIDCSettings, OIDCError, new_login_challenge,
                              authorization_url, verify_id_token)
except ImportError:
    jwt = None  # Optional auth dependencies are not needed for local-only Chatidy.


@unittest.skipIf(jwt is None, "Optional OIDC dependencies not installed")
class OIDCTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cls.jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(cls.key.public_key()))
        cls.jwk.update(kid="synthetic-key", alg="RS256", use="sig")
        cls.jwks = {"keys": [cls.jwk]}
        cls.issuer = "https://idp.example.invalid/application/o/test/"

    def token(self, **overrides):
        now = int(time.time())
        claims = {"iss": self.issuer, "sub": "synthetic-subject", "aud": "synthetic-client",
                  "iat": now, "exp": now + 600, "nonce": "synthetic-expected-nonce"}
        claims.update(overrides)
        return jwt.encode(claims, self.key, algorithm="RS256", headers={"kid": "synthetic-key"})

    def verify(self, token=None, jwks=None, **overrides):
        kwargs = {"issuer":self.issuer,"audience":"synthetic-client","nonce":"synthetic-expected-nonce"}
        kwargs.update(overrides)
        return verify_id_token(token if token is not None else self.token(),
                               jwks if jwks is not None else self.jwks, **kwargs)

    def test_valid_token_returns_only_stable_identity(self):
        self.assertEqual(self.verify(), {"issuer":self.issuer,"subject":"synthetic-subject"})

    def test_wrong_issuer_audience_nonce_and_expiration_fail_closed(self):
        now = int(time.time())
        for token in (self.token(iss="https://other.invalid/"),
                      self.token(aud="wrong-client"),
                      self.token(nonce="attacker-nonce"),
                      self.token(exp=now-120),
                      self.token(sub="")):
            with self.subTest(token=token[:12]), self.assertRaises(OIDCError):
                self.verify(token)

    def test_unknown_kid_duplicate_keys_and_unsigned_algorithm_fail(self):
        unknown = jwt.encode({"iss":self.issuer}, self.key, algorithm="RS256",
                             headers={"kid":"unknown"})
        for token,jwks in ((unknown,self.jwks),
                            (self.token(), {"keys":[self.jwk,self.jwk]}),
                            (self.token(), {"keys":[]})):
            with self.assertRaises(OIDCError):
                self.verify(token,jwks)
        unsigned = jwt.encode({"iss":self.issuer}, key="", algorithm="none", headers={"kid":"synthetic-key"})
        with self.assertRaises(OIDCError):
            self.verify(unsigned)

    def test_multiple_audiences_require_authorized_party(self):
        multi = self.token(aud=["synthetic-client","other"])
        with self.assertRaises(OIDCError):
            self.verify(multi)
        matched = self.token(aud=["synthetic-client","other"],azp="synthetic-client")
        self.assertEqual(self.verify(matched)["subject"],"synthetic-subject")

    def test_settings_disallow_cross_host_identity_endpoints(self):
        settings = OIDCSettings(self.issuer,
            self.issuer+"authorize/",self.issuer+"token/",self.issuer+"jwks/",
            "synthetic-client","https://app.example.invalid/auth/callback")
        settings.validate()
        state, nonce, verifier = new_login_challenge()
        params = parse_qs(urlsplit(authorization_url(settings,state,nonce,verifier)).query)
        self.assertEqual(params["response_type"],["code"])
        self.assertEqual(params["code_challenge_method"],["S256"])
        self.assertEqual(params["state"],[state])
        self.assertEqual(params["nonce"],[nonce])
        self.assertNotIn(verifier, str(params))
        with self.assertRaises(OIDCError):
            OIDCSettings(self.issuer,"https://evil.invalid/auth",settings.token_endpoint,
                         settings.jwks_uri,"synthetic-client",settings.redirect_uri).validate()


if __name__=="__main__":
    unittest.main()
