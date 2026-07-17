use std::collections::BTreeMap;

use serde::de::{DeserializeSeed, Error, MapAccess, SeqAccess, Visitor};

pub fn parse(bytes: &[u8]) -> Result<serde_json::Value, serde_json::Error> {
    struct Seed;
    struct ValueVisitor;

    impl<'de> DeserializeSeed<'de> for Seed {
        type Value = serde_json::Value;

        fn deserialize<D>(self, deserializer: D) -> Result<Self::Value, D::Error>
        where
            D: serde::Deserializer<'de>,
        {
            deserializer.deserialize_any(ValueVisitor)
        }
    }

    impl<'de> Visitor<'de> for ValueVisitor {
        type Value = serde_json::Value;

        fn expecting(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
            formatter.write_str("one strict JSON value")
        }

        fn visit_bool<E>(self, value: bool) -> Result<Self::Value, E> {
            Ok(value.into())
        }

        fn visit_i64<E>(self, value: i64) -> Result<Self::Value, E> {
            Ok(value.into())
        }

        fn visit_u64<E>(self, value: u64) -> Result<Self::Value, E> {
            Ok(value.into())
        }

        fn visit_f64<E>(self, value: f64) -> Result<Self::Value, E>
        where
            E: Error,
        {
            serde_json::Number::from_f64(value)
                .map(serde_json::Value::Number)
                .ok_or_else(|| E::custom("non-finite JSON number"))
        }

        fn visit_str<E>(self, value: &str) -> Result<Self::Value, E> {
            Ok(value.into())
        }

        fn visit_string<E>(self, value: String) -> Result<Self::Value, E> {
            Ok(value.into())
        }

        fn visit_none<E>(self) -> Result<Self::Value, E> {
            Ok(serde_json::Value::Null)
        }

        fn visit_unit<E>(self) -> Result<Self::Value, E> {
            Ok(serde_json::Value::Null)
        }

        fn visit_some<D>(self, deserializer: D) -> Result<Self::Value, D::Error>
        where
            D: serde::Deserializer<'de>,
        {
            Seed.deserialize(deserializer)
        }

        fn visit_seq<A>(self, mut sequence: A) -> Result<Self::Value, A::Error>
        where
            A: SeqAccess<'de>,
        {
            let mut values = Vec::new();
            while let Some(value) = sequence.next_element_seed(Seed)? {
                values.push(value);
            }
            Ok(values.into())
        }

        fn visit_map<A>(self, mut map: A) -> Result<Self::Value, A::Error>
        where
            A: MapAccess<'de>,
        {
            let mut values = BTreeMap::new();
            while let Some(key) = map.next_key::<String>()? {
                if values.contains_key(&key) {
                    return Err(A::Error::custom(format!("duplicate JSON member {key:?}")));
                }
                values.insert(key, map.next_value_seed(Seed)?);
            }
            Ok(serde_json::Value::Object(values.into_iter().collect()))
        }
    }

    let mut deserializer = serde_json::Deserializer::from_slice(bytes);
    let value = Seed.deserialize(&mut deserializer)?;
    deserializer.end()?;
    Ok(value)
}
