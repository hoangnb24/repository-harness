//! Phase 1 contract-test helper for strict Ed25519 verification.
//!
//! This is deliberately not the Repository Harness V1 runtime.  It gives the
//! Phase 1 fixture verifier a vetted cryptographic implementation without
//! carrying hand-written curve arithmetic in the Python contract checker.

use std::env;
use std::process::ExitCode;

use curve25519_dalek::edwards::CompressedEdwardsY;
use curve25519_dalek::scalar::Scalar;
use ed25519_dalek::{Signature, VerifyingKey};

fn decode_hex<const N: usize>(value: &str) -> Option<[u8; N]> {
    if value.len() != N * 2 || !value.bytes().all(|byte| byte.is_ascii_hexdigit()) {
        return None;
    }
    let mut result = [0_u8; N];
    for (index, pair) in value.as_bytes().chunks_exact(2).enumerate() {
        let high = (pair[0] as char).to_digit(16)? as u8;
        let low = (pair[1] as char).to_digit(16)? as u8;
        result[index] = (high << 4) | low;
    }
    Some(result)
}

fn decode_message(value: &str) -> Option<Vec<u8>> {
    if !value.len().is_multiple_of(2) || !value.bytes().all(|byte| byte.is_ascii_hexdigit()) {
        return None;
    }
    value
        .as_bytes()
        .chunks_exact(2)
        .map(|pair| {
            let high = (pair[0] as char).to_digit(16)? as u8;
            let low = (pair[1] as char).to_digit(16)? as u8;
            Some((high << 4) | low)
        })
        .collect()
}

fn canonical_torsion_free_point(encoded: &[u8; 32]) -> bool {
    let compressed = CompressedEdwardsY(*encoded);
    let Some(point) = compressed.decompress() else {
        return false;
    };
    point.compress().to_bytes() == *encoded && !point.is_small_order() && point.is_torsion_free()
}

fn strict_public_key(public_key: &[u8; 32]) -> bool {
    canonical_torsion_free_point(public_key) && VerifyingKey::from_bytes(public_key).is_ok()
}

fn strict_verify(public_key: &[u8; 32], message: &[u8], signature: &[u8; 64]) -> bool {
    let encoded_r: &[u8; 32] = signature[..32].try_into().expect("fixed signature prefix");
    let encoded_s: &[u8; 32] = signature[32..].try_into().expect("fixed signature suffix");
    let scalar = Option::<Scalar>::from(Scalar::from_canonical_bytes(*encoded_s));
    if !strict_public_key(public_key)
        || !canonical_torsion_free_point(encoded_r)
        || scalar.is_none_or(|value| value == Scalar::ZERO)
    {
        return false;
    }
    let Ok(verifying_key) = VerifyingKey::from_bytes(public_key) else {
        return false;
    };
    verifying_key
        .verify_strict(message, &Signature::from_bytes(signature))
        .is_ok()
}

fn usage() -> ExitCode {
    eprintln!("usage: v1-contract-crypto public-key <public-hex> | verify <public-hex> <message-hex> <signature-hex>");
    ExitCode::from(2)
}

fn main() -> ExitCode {
    let arguments: Vec<String> = env::args().skip(1).collect();
    match arguments.as_slice() {
        [command, public] if command == "public-key" => {
            let Some(public_key) = decode_hex::<32>(public) else {
                return ExitCode::from(2);
            };
            ExitCode::from(u8::from(!strict_public_key(&public_key)))
        }
        [command, public, message, signature] if command == "verify" => {
            let (Some(public_key), Some(message), Some(signature)) = (
                decode_hex::<32>(public),
                decode_message(message),
                decode_hex::<64>(signature),
            ) else {
                return ExitCode::from(2);
            };
            ExitCode::from(u8::from(!strict_verify(&public_key, &message, &signature)))
        }
        _ => usage(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    const IDENTITY: [u8; 32] = {
        let mut value = [0_u8; 32];
        value[0] = 1;
        value
    };

    #[test]
    fn rejects_identity_and_order_two_public_keys() {
        let mut order_two = [0xff_u8; 32];
        order_two[0] = 0xec;
        order_two[31] = 0x7f;
        assert!(!strict_public_key(&IDENTITY));
        assert!(!strict_public_key(&order_two));
    }

    #[test]
    fn rejects_zero_scalar_identity_forgery() {
        let mut signature = [0_u8; 64];
        signature[..32].copy_from_slice(&IDENTITY);
        assert!(!strict_verify(&IDENTITY, b"forged", &signature));
    }
}
