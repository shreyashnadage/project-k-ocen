# Copyright (c) 2026, Project K
# License: MIT
"""
RFC 7515 Appendix F detached-content JWS verification.

Assumed header format: "<base64url header>..<base64url signature>" (the
empty middle segment is where the payload would normally sit — detached
JWS omits it and the payload is supplied out-of-band instead, here as the
raw HTTP request body). This is the convention India's Account
Aggregator/ReBIT API specs use for request signing, which the OCEN
ecosystem generally follows — but this has NOT been confirmed against
real OCEN sandbox traffic (spec §6.5 — do that before trusting this in
anything beyond dev). If the real header name or JWS shape differs, fix it
here; the rest of the webhook handling doesn't need to change.

Deliberately a standalone module with no Frappe request/response coupling
so it can be unit tested directly (see the test used to verify this during
development — a self-signed RSA keypair proves the crypto is correct
without needing real OCEN credentials).
"""

import base64

import jwt


class SignatureVerificationError(Exception):
	pass


def verify_detached_jws(payload_bytes: bytes, signature_header: str | None, public_key_pem: str) -> dict:
	"""Verify `signature_header` as a detached JWS over `payload_bytes`,
	signed with the private counterpart of `public_key_pem` (RS256 only —
	never trust an `alg` claimed by the token itself). Returns the parsed
	JSON payload on success. Raises SignatureVerificationError on any
	failure — malformed header, wrong key, tampered payload, all collapse
	to the same exception type so callers don't need to distinguish them.
	"""
	if not signature_header:
		raise SignatureVerificationError("Missing signature header.")
	if not public_key_pem:
		raise SignatureVerificationError("No registry public key configured to verify against.")
	if ".." not in signature_header:
		raise SignatureVerificationError(
			"Malformed detached JWS (expected '<header>..<signature>')."
		)

	header_b64, _, sig_b64 = signature_header.partition("..")
	if not header_b64 or not sig_b64:
		raise SignatureVerificationError("Malformed detached JWS: empty header or signature segment.")

	payload_b64 = base64.urlsafe_b64encode(payload_bytes).rstrip(b"=").decode("ascii")
	reassembled_token = f"{header_b64}.{payload_b64}.{sig_b64}"

	try:
		return jwt.decode(reassembled_token, public_key_pem, algorithms=["RS256"])
	except jwt.exceptions.InvalidTokenError as exc:
		raise SignatureVerificationError(f"JWS verification failed: {exc}") from exc


def sign_detached_jws(payload_bytes: bytes, private_key_pem: str) -> str:
	"""Inverse of verify_detached_jws — produces the detached-JWS header
	value for an outbound request body. Used by OCENSettings.sign_request
	and by the test that proves verify_detached_jws actually rejects a
	tampered payload (sign real bytes, mutate them, confirm verification
	fails).
	"""
	from jwt.algorithms import RSAAlgorithm

	# A throwaway full (non-detached) encode just to get PyJWT's own
	# standard JWS header (alg/typ) as base64url, so the header this
	# produces matches what PyJWT itself would verify — rather than
	# hand-building the header JSON and risking a mismatch.
	throwaway_token = jwt.encode({}, private_key_pem, algorithm="RS256")
	header_b64, _, _ = throwaway_token.partition(".")

	payload_b64 = base64.urlsafe_b64encode(payload_bytes).rstrip(b"=").decode("ascii")
	signing_input = f"{header_b64}.{payload_b64}".encode("ascii")

	algo = RSAAlgorithm(RSAAlgorithm.SHA256)
	private_key = algo.prepare_key(private_key_pem)
	signature = algo.sign(signing_input, private_key)
	sig_b64 = base64.urlsafe_b64encode(signature).rstrip(b"=").decode("ascii")

	return f"{header_b64}..{sig_b64}"
