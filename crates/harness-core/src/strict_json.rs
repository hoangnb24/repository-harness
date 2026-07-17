use std::collections::BTreeMap;
use std::fmt;

use serde::de::{DeserializeSeed, Error as _, MapAccess, SeqAccess, Visitor};
use serde_json::{Map, Number, Value};
use sha2::{Digest, Sha256};

const MAX_INTEROPERABLE_INTEGER: u64 = 9_007_199_254_740_991;

pub fn parse(bytes: &[u8]) -> Result<Value, String> {
    let mut deserializer = serde_json::Deserializer::from_slice(bytes);
    let value = StrictValueSeed
        .deserialize(&mut deserializer)
        .map_err(|error| error.to_string())?;
    deserializer.end().map_err(|error| error.to_string())?;
    Ok(value)
}

struct StrictValueSeed;

impl<'de> DeserializeSeed<'de> for StrictValueSeed {
    type Value = Value;

    fn deserialize<D>(self, deserializer: D) -> Result<Self::Value, D::Error>
    where
        D: serde::Deserializer<'de>,
    {
        deserializer.deserialize_any(StrictValueVisitor)
    }
}

struct StrictValueVisitor;

impl<'de> Visitor<'de> for StrictValueVisitor {
    type Value = Value;

    fn expecting(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str("closed RFC 8785-compatible JSON")
    }

    fn visit_bool<E>(self, value: bool) -> Result<Self::Value, E> {
        Ok(Value::Bool(value))
    }

    fn visit_i64<E>(self, value: i64) -> Result<Self::Value, E>
    where
        E: serde::de::Error,
    {
        if value.unsigned_abs() > MAX_INTEROPERABLE_INTEGER {
            return Err(E::custom("integer is outside the interoperable range"));
        }
        Ok(Value::Number(Number::from(value)))
    }

    fn visit_u64<E>(self, value: u64) -> Result<Self::Value, E>
    where
        E: serde::de::Error,
    {
        if value > MAX_INTEROPERABLE_INTEGER {
            return Err(E::custom("integer is outside the interoperable range"));
        }
        Ok(Value::Number(Number::from(value)))
    }

    fn visit_f64<E>(self, _value: f64) -> Result<Self::Value, E>
    where
        E: serde::de::Error,
    {
        Err(E::custom("floating-point numbers are forbidden"))
    }

    fn visit_str<E>(self, value: &str) -> Result<Self::Value, E> {
        Ok(Value::String(value.into()))
    }

    fn visit_string<E>(self, value: String) -> Result<Self::Value, E> {
        Ok(Value::String(value))
    }

    fn visit_none<E>(self) -> Result<Self::Value, E> {
        Ok(Value::Null)
    }

    fn visit_unit<E>(self) -> Result<Self::Value, E> {
        Ok(Value::Null)
    }

    fn visit_seq<A>(self, mut values: A) -> Result<Self::Value, A::Error>
    where
        A: SeqAccess<'de>,
    {
        let mut result = Vec::new();
        while let Some(value) = values.next_element_seed(StrictValueSeed)? {
            result.push(value);
        }
        Ok(Value::Array(result))
    }

    fn visit_map<A>(self, mut values: A) -> Result<Self::Value, A::Error>
    where
        A: MapAccess<'de>,
    {
        let mut result = Map::new();
        while let Some(key) = values.next_key::<String>()? {
            if result.contains_key(&key) {
                return Err(A::Error::custom(format!("duplicate JSON member: {key}")));
            }
            result.insert(key, values.next_value_seed(StrictValueSeed)?);
        }
        Ok(Value::Object(result))
    }
}

pub fn canonical(value: &Value) -> Result<Vec<u8>, String> {
    fn render(value: &Value, output: &mut String) -> Result<(), String> {
        match value {
            Value::Null => output.push_str("null"),
            Value::Bool(true) => output.push_str("true"),
            Value::Bool(false) => output.push_str("false"),
            Value::Number(number) if number.is_i64() || number.is_u64() => {
                output.push_str(&number.to_string());
            }
            Value::Number(_) => return Err("floating-point numbers are forbidden".into()),
            Value::String(string) => {
                output.push_str(&serde_json::to_string(string).map_err(|error| error.to_string())?)
            }
            Value::Array(values) => {
                output.push('[');
                for (index, child) in values.iter().enumerate() {
                    if index > 0 {
                        output.push(',');
                    }
                    render(child, output)?;
                }
                output.push(']');
            }
            Value::Object(values) => {
                output.push('{');
                let mut ordered: BTreeMap<Vec<u16>, (&String, &Value)> = BTreeMap::new();
                for (key, child) in values {
                    ordered.insert(key.encode_utf16().collect(), (key, child));
                }
                for (index, (_, (key, child))) in ordered.into_iter().enumerate() {
                    if index > 0 {
                        output.push(',');
                    }
                    output
                        .push_str(&serde_json::to_string(key).map_err(|error| error.to_string())?);
                    output.push(':');
                    render(child, output)?;
                }
                output.push('}');
            }
        }
        Ok(())
    }

    let mut output = String::new();
    render(value, &mut output)?;
    Ok(output.into_bytes())
}

pub fn digest(value: &Value) -> Result<String, String> {
    Ok(hex_sha256(&canonical(value)?))
}

pub fn signed_message(domain: &str, value: &Value) -> Result<[u8; 32], String> {
    let mut hasher = Sha256::new();
    hasher.update(domain.as_bytes());
    hasher.update([0]);
    hasher.update(canonical(value)?);
    Ok(hasher.finalize().into())
}

pub fn hex_sha256(bytes: &[u8]) -> String {
    format!("{:x}", Sha256::digest(bytes))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn rejects_duplicate_members_and_floats() {
        assert!(parse(br#"{"a":1,"a":2}"#).is_err());
        assert!(parse(br#"{"a":1.5}"#).is_err());
    }

    #[test]
    fn canonicalization_ignores_member_order_and_whitespace() {
        let left = parse(br#"{"z":1,"a":"ok"}"#).unwrap();
        let right = parse(b"{ \"a\" : \"ok\", \"z\" : 1 }").unwrap();
        assert_eq!(canonical(&left).unwrap(), canonical(&right).unwrap());
    }
}
